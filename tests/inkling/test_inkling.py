"""Offline transport and contract tests for Inkling."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

MAIN = Path(__file__).resolve().parents[2] / 'skills' / 'inkling' / 'main.py'
BASE = 'https://api.inkling.buildersoft.io/v1'
KEY = 'test-key-do-not-leak'


class CountingStream(io.BytesIO):
    consumed = 0

    def read(self, size=-1):
        data = super().read(size)
        self.consumed += len(data)
        return data


class Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.data if isinstance(self.data, bytes) else json.dumps(self.data).encode()


def call(tool, args=None, response=None, failure=None, key=KEY):
    output = io.StringIO()
    calls = []
    payload = {'data': [{'extra': 7}], 'next_cursor': 'next', 'truncated': True} if response is None else response

    class Opener:
        def open(self, req, timeout):
            calls.append((req, timeout))
            if failure:
                raise failure
            return Response(payload)

    with patch('urllib.request.build_opener', return_value=Opener()) as factory, contextlib.redirect_stdout(output):
        runpy.run_path(str(MAIN), init_globals={'params': {'tool': 'inkling.' + tool, 'apiKey': key, **(args or {})}})
    return json.loads(output.getvalue()), calls, factory


class InklingTests(unittest.TestCase):
    def test_all_routes(self):
        cases = [
            ('usage', {}, 'GET', '/usage', None),
            ('list_notes', {'q': 'hello', 'archived': False, 'limit': 2, 'cursor': 'a'}, 'GET', '/notes', None),
            ('get_note', {'id': 'note/a?b'}, 'GET', '/notes/note%2Fa%3Fb', None),
            ('list_todos', {'view': 'done', 'tag': 'x', 'cursor': 'c'}, 'GET', '/todos', None),
            ('ask', {'query': 'Why?', 'discussion_id': 'disc_1'}, 'POST', '/ask', {'query': 'Why?', 'discussion_id': 'disc_1'}),
            ('get_answer', {'id': 'ans_1', 'wait': 20}, 'GET', '/answers/ans_1', None),
            ('list_discussions', {'archived': True, 'limit': 1, 'cursor': 'c'}, 'GET', '/discussions', None),
            ('get_discussion', {'id': 'disc_1'}, 'GET', '/discussions/disc_1', None),
            ('create_note', {'title': 't', 'body': 'b', 'tags': ['a'], 'properties': {'due': None}, 'sources': [], 'share_with': []}, 'POST', '/notes', {'title': 't', 'body': 'b', 'tags': ['a'], 'properties': {'due': None}, 'sources': [], 'share_with': []}),
            ('update_note', {'id': 'n', 'body': 'b', 'if_match': 'etag', 'properties': {'status': None}}, 'PATCH', '/notes/n', {'body': 'b', 'properties': {'status': None}}),
            ('append_note', {'id': 'n', 'body': 'b', 'sources': []}, 'POST', '/notes/n/append', {'body': 'b', 'sources': []}),
            ('archive_note', {'id': 'n'}, 'POST', '/notes/n/archive', None),
            ('create_todo', {'text': 'todo', 'note_id': 'n', 'due': '2026-01-01', 'priority': 1, 'repeat': 'daily'}, 'POST', '/todos', {'text': 'todo', 'note_id': 'n', 'due': '2026-01-01', 'priority': 1, 'repeat': 'daily'}),
            ('complete_todo', {'id': 't'}, 'POST', '/todos/t/complete', None),
        ]
        for tool, args, method, path, body in cases:
            with self.subTest(tool=tool):
                out, calls, factory = call(tool, args)
                self.assertEqual(out, {'data': [{'extra': 7}], 'next_cursor': 'next', 'truncated': True})
                self.assertEqual(len(calls), 1)
                req, timeout = calls[0]
                self.assertEqual(req.method, method)
                self.assertEqual(urlsplit(req.full_url).path, '/v1' + path)
                self.assertTrue(req.full_url.startswith(BASE + '/'))
                self.assertEqual(req.get_header('Authorization'), 'Bearer ' + KEY)
                self.assertEqual(timeout, 30)
                self.assertEqual(json.loads(req.data) if req.data else None, body)
                self.assertEqual(req.get_header('Content-type'), 'application/json' if body is not None else None)
                self.assertEqual(type(factory.call_args.args[0]).__name__, 'NoRedirect')

    def test_query_pagination_and_booleans(self):
        _, calls, _ = call('list_notes', {'q': 'x y', 'tag': '#a', 'status': 'done', 'archived': False, 'cursor': 'a+b', 'limit': 50})
        self.assertEqual(parse_qs(urlsplit(calls[0][0].full_url).query), {'q': ['x y'], 'tag': ['#a'], 'status': ['done'], 'archived': ['false'], 'cursor': ['a+b'], 'limit': ['50']})
        _, calls, _ = call('list_todos', {'view': 'done', 'cursor': 'c'})
        self.assertEqual(parse_qs(urlsplit(calls[0][0].full_url).query), {'view': ['done'], 'cursor': ['c']})

    def test_todo_empty_or_absent_cursor_is_not_sent(self):
        for view in (None, 'open', 'assigned', 'done'):
            for cursor_args in ({}, {'cursor': None}, {'cursor': ''}):
                with self.subTest(view=view, cursor_args=cursor_args):
                    args = {'tag': '', **cursor_args}
                    expected = {'tag': ['']}
                    if view is not None:
                        args['view'] = view
                        expected['view'] = [view]
                    out, calls, _ = call('list_todos', args)
                    self.assertNotIn('error', out)
                    self.assertEqual(len(calls), 1)
                    query = parse_qs(urlsplit(calls[0][0].full_url).query, keep_blank_values=True)
                    self.assertEqual(query, expected)

    def test_todo_nonempty_cursor_requires_done_view(self):
        for view_args in ({}, {'view': 'open'}, {'view': 'assigned'}):
            with self.subTest(view_args=view_args):
                out, calls, _ = call('list_todos', {**view_args, 'cursor': 'next-page'})
                self.assertEqual(out, {'error': 'cursor is only supported for the done view'})
                self.assertEqual(calls, [])
        _, calls, _ = call('list_todos', {'view': 'done', 'cursor': 'a+b/='})
        query = parse_qs(urlsplit(calls[0][0].full_url).query, keep_blank_values=True)
        self.assertEqual(query, {'view': ['done'], 'cursor': ['a+b/=']})

    def test_todo_invalid_cursor_types_make_no_request(self):
        for cursor in (False, 0, [], {}):
            with self.subTest(cursor=cursor):
                out, calls, _ = call('list_todos', {'view': 'done', 'cursor': cursor})
                self.assertEqual(out, {'error': 'cursor must be a string'})
                self.assertEqual(calls, [])

    def test_conditional_and_idempotency_headers(self):
        for tool, args in [('create_note', {'title': 'x'}), ('append_note', {'id': 'n', 'body': 'x'}), ('create_todo', {'text': 'x'})]:
            with self.subTest(tool=tool):
                _, calls, _ = call(tool, {**args, 'idempotency_key': 'once-1'})
                self.assertEqual(calls[0][0].get_header('Idempotency-key'), 'once-1')
        _, calls, _ = call('update_note', {'id': 'n', 'body': 'x', 'if_match': '"etag"'})
        self.assertEqual(calls[0][0].get_header('If-match'), '"etag"')

    def test_invalid_arguments_make_no_request(self):
        cases = [('ask', {'query': ''}), ('ask', {'query': 'x' * 4001}), ('get_answer', {'id': 'a', 'wait': 21}), ('get_answer', {'id': 'a', 'wait': True}), ('list_todos', {'view': 'open', 'cursor': 'c'}), ('list_todos', {'view': 'bad'}), ('list_notes', {'q': 'x' * 201}), ('get_note', {'id': '..'}), ('update_note', {'id': 'n', 'body': 'x'}), ('update_note', {'id': 'n'}), ('create_note', {'title': ''}), ('append_note', {'id': 'n'}), ('create_todo', {'text': '   '}), ('create_note', {'title': 'x', 'idempotency_key': 'bad\r\nheader'})]
        for tool, args in cases:
            with self.subTest(tool=tool, args=args):
                out, calls, _ = call(tool, args)
                self.assertIn('error', out)
                self.assertEqual(calls, [])

    def test_http_errors_redact_and_never_retry(self):
        for code, body in [(400, b'{"detail":"test-key-do-not-leak"}'), (429, b'not json test-key-do-not-leak'), (302, b'redirect')]:
            with self.subTest(code=code):
                exc = HTTPError(BASE, code, 'error', {'Retry-After': '5', 'Location': 'https://evil.invalid/'}, io.BytesIO(body))
                out, calls, _ = call('create_todo', {'text': 'x'}, failure=exc)
                self.assertEqual(out['status'], code)
                self.assertEqual(out['retry_after'], '5')
                self.assertNotIn(KEY, json.dumps(out))
                self.assertEqual(len(calls), 1)

    def test_problem_codes_and_correlation_are_bounded_and_redacted(self):
        correlation = '4bf92f3577b34da6a3ce929d0e0e4736'
        for status in (401, 403, 409, 412, 428, 429, 503):
            with self.subTest(status=status):
                body = json.dumps({'code': 'insufficient_scope', 'correlation_id': correlation, 'detail': KEY}).encode()
                exc = HTTPError(BASE, status, 'error', {'Retry-After': '5'}, io.BytesIO(body))
                out, calls, _ = call('usage', failure=exc)
                self.assertEqual(out['code'], 'insufficient_scope')
                self.assertEqual(out['correlation_id'], correlation)
                self.assertEqual(out['status'], status)
                self.assertNotIn(KEY, json.dumps(out))
                self.assertEqual(len(calls), 1)
        for body in (
            {'code': KEY, 'correlation_id': KEY},
            {'code': 'leak ' + KEY, 'correlation_id': 'bad/value'},
            {'code': 'a' * 129, 'correlation_id': 'a' * 129},
        ):
            with self.subTest(body=body):
                exc = HTTPError(BASE, 400, 'error', {}, io.BytesIO(json.dumps(body).encode()))
                out, _, _ = call('usage', failure=exc)
                self.assertNotIn('code', out)
                self.assertNotIn('correlation_id', out)
                self.assertNotIn(KEY, json.dumps(out))

    def test_problem_body_read_is_capped_and_invalid_json_is_safe(self):
        for raw in (b'not json', b'{"code":"invalid_request"}' + b' ' * 20000):
            with self.subTest(size=len(raw)):
                stream = CountingStream(raw)
                exc = HTTPError(BASE, 503, 'error', {}, stream)
                out, _, _ = call('usage', failure=exc)
                self.assertEqual(out['status'], 503)
                self.assertNotIn('code', out)
                self.assertLessEqual(stream.consumed, 16385)

    def test_network_error_and_credentials(self):
        out, calls, _ = call('usage', failure=URLError(KEY))
        self.assertNotIn(KEY, json.dumps(out))
        self.assertEqual(len(calls), 1)
        out, calls, _ = call('usage', key='')
        self.assertIn('error', out)
        self.assertEqual(calls, [])

    def test_redirect_handler_refuses_redirect(self):
        _, _, factory = call('usage')
        handler = factory.call_args.args[0]
        self.assertIsNone(handler.redirect_request(None, None, 302, 'Found', {}, 'https://evil.invalid'))


SOURCE = {'n': 1, 'url': 'https://example.com/a', 'title': 't', 'snippet': 's', 'published_date': '2026'}
FULL_ARGS = {
    'usage': {},
    'list_notes': {'limit': 5, 'cursor': 'c', 'q': 'q', 'tag': 't', 'status': 'waiting', 'archived': True},
    'get_note': {'id': 'n'},
    'list_todos': {'view': 'done', 'tag': 't', 'cursor': 'c'},
    'ask': {'query': 'q', 'discussion_id': None},
    'get_answer': {'id': 'a', 'wait': 0},
    'list_discussions': {'limit': 5, 'cursor': 'c', 'archived': False},
    'get_discussion': {'id': 'd'},
    'create_note': {'title': 't', 'body': None, 'tags': ['a'], 'properties': {'status': 'done', 'due': '2026-02-28', 'lead': 'me'}, 'sources': [SOURCE], 'share_with': [{'email': 'a@example.com', 'role': 'view'}], 'idempotency_key': 'k'},
    'update_note': {'id': 'n', 'title': 't', 'body': 'b', 'tags': ['a'], 'properties': {'status': None, 'due': None, 'lead': 'person_key'}, 'sources': [SOURCE], 'if_match': 'e'},
    'append_note': {'id': 'n', 'body': 'b', 'sources': [SOURCE], 'idempotency_key': 'k'},
    'archive_note': {'id': 'n'},
    'create_todo': {'text': 't', 'note_id': None, 'due': '2024-02-29', 'priority': 2, 'repeat': 'yearly-02-29', 'idempotency_key': 'k'},
    'complete_todo': {'id': 't'},
}


def sent(tool, args):
    out, calls, _ = call(tool, args)
    return out, calls, (json.loads(calls[0][0].data) if calls and calls[0][0].data else None)


class SchemaTests(unittest.TestCase):
    manifest = json.loads((MAIN.parent / 'manifest.json').read_text(encoding='utf-8'))
    tools = {t['name'].split('.', 1)[1]: t for t in manifest['tools']}

    def test_manifest_and_handlers_have_parity(self):
        self.assertEqual(set(self.tools), set(FULL_ARGS))
        self.assertEqual(len(self.tools), 14)
        for name, tool in self.tools.items():
            with self.subTest(tool=name):
                declared = set(tool['parameters']['properties'])
                self.assertEqual(declared, set(FULL_ARGS[name]))
                self.assertLessEqual(set(tool['parameters'].get('required', [])), declared)
                out, calls, _ = call(name, FULL_ARGS[name])
                self.assertNotIn('error', out)
                self.assertEqual(len(calls), 1)

    def test_manifest_nested_contracts(self):
        props = self.tools['create_note']['parameters']['properties']
        update = self.tools['update_note']['parameters']['properties']
        for note in (props, update):
            self.assertEqual(note['sources']['type'], ['array', 'null'])
            self.assertEqual(note['sources']['maxItems'], 100)
            item = note['sources']['items']
            self.assertEqual(item['required'], ['n', 'url'])
            self.assertEqual((item['properties']['n']['minimum'], item['properties']['n']['maximum']), (1, 999))
            self.assertEqual(item['properties']['url']['maxLength'], 2048)
            self.assertEqual(item['properties']['title']['type'], ['string', 'null'])
            self.assertEqual(note['tags']['maxItems'], 50)
            self.assertEqual(note['properties']['properties']['status']['enum'], ['not_started', 'in_progress', 'waiting', 'done', None])
            self.assertEqual(sorted(note['properties']['properties']), ['due', 'lead', 'status'])
            self.assertEqual(note['body']['type'], ['string', 'null'])
        share = props['share_with']
        self.assertEqual((share['maxItems'], share['items']['required']), (9, ['email', 'role']))
        self.assertEqual(share['items']['properties']['role']['enum'], ['edit', 'view'])
        self.assertEqual(update['title']['type'], ['string', 'null'])
        self.assertEqual(self.tools['create_todo']['parameters']['properties']['priority']['enum'], [1, 2, None])
        self.assertEqual(self.tools['ask']['parameters']['properties']['discussion_id']['type'], ['string', 'null'])
        self.assertEqual(self.tools['append_note']['parameters']['required'], ['id', 'body'])
        self.assertNotIn('limit', self.tools['list_todos']['parameters']['properties'])

    def test_sandbox_timeout_exceeds_transport_timeout(self):
        self.assertEqual(self.manifest['sandbox']['timeoutSeconds'], 45)
        _, calls, _ = call('usage')
        self.assertLess(calls[0][1], self.manifest['sandbox']['timeoutSeconds'])

    def test_valid_nulls_are_sent_so_fields_can_be_cleared(self):
        _, _, body = sent('create_note', {'title': 't', 'body': None, 'tags': None, 'properties': None, 'sources': None, 'share_with': None})
        self.assertEqual(body, {'title': 't', 'body': None, 'tags': None, 'properties': None, 'sources': None, 'share_with': None})
        props = {'status': None, 'due': None, 'lead': None}
        _, _, body = sent('update_note', {'id': 'n', 'title': None, 'tags': None, 'properties': props, 'sources': None})
        self.assertEqual(body, {'title': None, 'tags': None, 'properties': props, 'sources': None})
        _, _, body = sent('create_todo', {'text': 't', 'note_id': None, 'due': None, 'priority': None, 'repeat': None})
        self.assertEqual(body, {'text': 't', 'note_id': None, 'due': None, 'priority': None, 'repeat': None})
        _, _, body = sent('ask', {'query': 'q', 'discussion_id': None})
        self.assertEqual(body, {'query': 'q', 'discussion_id': None})
        _, _, body = sent('append_note', {'id': 'n', 'body': 'b', 'sources': None})
        self.assertEqual(body, {'body': 'b', 'sources': None})
        _, _, body = sent('update_note', {'id': 'n', 'body': None, 'if_match': 'e'})
        self.assertEqual(body, {'body': None})

    def test_valid_nested_values_are_forwarded_unchanged(self):
        for tool, args in [('create_note', FULL_ARGS['create_note']), ('update_note', FULL_ARGS['update_note'])]:
            body_args = {k: v for k, v in args.items() if k not in ('id', 'if_match', 'idempotency_key')}
            _, _, body = sent(tool, args)
            self.assertEqual(body, body_args)
        for repeat in ['daily', 'weekdays', 'weekly-1', 'weekly-7', 'monthly-1', 'monthly-31', 'yearly-12-31']:
            with self.subTest(repeat=repeat):
                out, calls, _ = call('create_todo', {'text': 't', 'repeat': repeat})
                self.assertNotIn('error', out)
                self.assertEqual(len(calls), 1)
        sources = [{'n': 999, 'url': 'http://example.com/' + 'a' * 2000}, {'n': 1, 'url': 'https://example.com', 'title': None}]
        _, _, body = sent('create_note', {'title': 't', 'sources': sources})
        self.assertEqual(body['sources'], sources)
        _, _, body = sent('create_note', {'title': 't', 'tags': ['x'] * 50, 'sources': [{'n': i, 'url': 'https://e.com'} for i in range(1, 101)], 'share_with': [{'email': 'a@b.c', 'role': 'edit'}] * 9})
        self.assertEqual((len(body['tags']), len(body['sources']), len(body['share_with'])), (50, 100, 9))

    def test_invalid_nested_values_make_no_request(self):
        good = {'n': 1, 'url': 'https://e.com'}
        cases = [
            ('create_note', {'title': 'x', 'body': 5}),
            ('create_note', {'title': 'x', 'tags': 'a'}),
            ('create_note', {'title': 'x', 'tags': ['a'] * 51}),
            ('create_note', {'title': 'x', 'tags': ['#a']}),
            ('create_note', {'title': 'x', 'tags': ['']}),
            ('create_note', {'title': 'x', 'tags': [1]}),
            ('create_note', {'title': 'x', 'properties': []}),
            ('create_note', {'title': 'x', 'properties': {'other': 1}}),
            ('create_note', {'title': 'x', 'properties': {'status': 'bad'}}),
            ('create_note', {'title': 'x', 'properties': {'status': ['done']}}),
            ('create_note', {'title': 'x', 'properties': {'due': '2026-02-30'}}),
            ('create_note', {'title': 'x', 'properties': {'due': '2026-1-1'}}),
            ('create_note', {'title': 'x', 'properties': {'due': 20260101}}),
            ('create_note', {'title': 'x', 'properties': {'lead': 'person_key'}}),
            ('update_note', {'id': 'n', 'properties': {'lead': ''}}),
            ('update_note', {'id': 'n', 'properties': {'lead': 7}}),
            ('create_note', {'title': 'x', 'sources': 'a'}),
            ('create_note', {'title': 'x', 'sources': [good] * 101}),
            ('create_note', {'title': 'x', 'sources': ['a']}),
            ('create_note', {'title': 'x', 'sources': [{'url': 'https://e.com'}]}),
            ('create_note', {'title': 'x', 'sources': [{'n': 0, 'url': 'https://e.com'}]}),
            ('create_note', {'title': 'x', 'sources': [{'n': 1000, 'url': 'https://e.com'}]}),
            ('create_note', {'title': 'x', 'sources': [{'n': True, 'url': 'https://e.com'}]}),
            ('create_note', {'title': 'x', 'sources': [{'n': '1', 'url': 'https://e.com'}]}),
            ('create_note', {'title': 'x', 'sources': [good, good]}),
            ('create_note', {'title': 'x', 'sources': [{'n': 1}]}),
            ('create_note', {'title': 'x', 'sources': [{'n': 1, 'url': 'ftp://e.com'}]}),
            ('create_note', {'title': 'x', 'sources': [{'n': 1, 'url': 'https://'}]}),
            ('create_note', {'title': 'x', 'sources': [{'n': 1, 'url': 'https://e.com/' + 'a' * 2048}]}),
            ('create_note', {'title': 'x', 'sources': [{**good, 'title': 5}]}),
            ('create_note', {'title': 'x', 'sources': [{**good, 'snippet': []}]}),
            ('create_note', {'title': 'x', 'sources': [{**good, 'published_date': 2026}]}),
            ('create_note', {'title': 'x', 'sources': [{**good, 'extra': 1}]}),
            ('create_note', {'title': 'x', 'share_with': 'a'}),
            ('create_note', {'title': 'x', 'share_with': [{'email': 'a@b.c', 'role': 'edit'}] * 10}),
            ('create_note', {'title': 'x', 'share_with': [{'email': 'a@b.c'}]}),
            ('create_note', {'title': 'x', 'share_with': [{'role': 'edit'}]}),
            ('create_note', {'title': 'x', 'share_with': [{'email': 'a@b.c', 'role': 'owner'}]}),
            ('create_note', {'title': 'x', 'share_with': [{'email': 'nope', 'role': 'edit'}]}),
            ('create_note', {'title': 'x', 'share_with': [{'email': 'a@b.c', 'role': 'edit', 'x': 1}]}),
            ('create_note', {'title': 5}),
            ('create_note', {}),
            ('update_note', {'id': 'n', 'title': ''}),
            ('update_note', {'id': 'n', 'title': 5}),
            ('update_note', {'id': 'n', 'body': 5, 'if_match': 'e'}),
            ('update_note', {'id': 'n', 'body': None}),
            ('update_note', {'id': 'n', 'sources': [{'n': 1}]}),
            ('update_note', {'id': 'n', 'tags': ['#a']}),
            ('update_note', {'id': 'n', 'title': 'x', 'if_match': 'bad\nvalue'}),
            ('update_note', {'id': ''}),
            ('append_note', {'id': 'n', 'body': None}),
            ('append_note', {'id': 'n', 'body': 'b', 'sources': [{'n': 1, 'url': 'javascript:alert(1)'}]}),
            ('append_note', {'body': 'b'}),
            ('create_todo', {'text': 5}),
            ('create_todo', {'text': 'x' * 2001}),
            ('create_todo', {'text': 'x', 'note_id': ''}),
            ('create_todo', {'text': 'x', 'note_id': 5}),
            ('create_todo', {'text': 'x', 'due': '2026-13-01'}),
            ('create_todo', {'text': 'x', 'due': 'tomorrow'}),
            ('create_todo', {'text': 'x', 'priority': 3}),
            ('create_todo', {'text': 'x', 'priority': 0}),
            ('create_todo', {'text': 'x', 'priority': True}),
            ('create_todo', {'text': 'x', 'priority': '1'}),
            ('create_todo', {'text': 'x', 'repeat': 'hourly'}),
            ('create_todo', {'text': 'x', 'repeat': 'weekly-0'}),
            ('create_todo', {'text': 'x', 'repeat': 'weekly-8'}),
            ('create_todo', {'text': 'x', 'repeat': 'monthly-0'}),
            ('create_todo', {'text': 'x', 'repeat': 'monthly-32'}),
            ('create_todo', {'text': 'x', 'repeat': 'yearly-02-30'}),
            ('create_todo', {'text': 'x', 'repeat': 'yearly-13-01'}),
            ('create_todo', {'text': 'x', 'repeat': 5}),
            ('ask', {'query': 5}),
            ('ask', {'query': 'x', 'discussion_id': ''}),
            ('ask', {'query': 'x', 'discussion_id': 5}),
            ('list_notes', {'status': 'bad'}),
            ('list_notes', {'archived': 'false'}),
            ('list_notes', {'cursor': 5}),
            ('list_notes', {'tag': ['a']}),
            ('list_notes', {'q': 5}),
            ('list_discussions', {'archived': 1}),
            ('list_discussions', {'cursor': 5}),
            ('list_todos', {'tag': 5}),
            ('list_todos', {'view': 5}),
            ('get_answer', {'id': 'a', 'wait': -1}),
            ('get_answer', {'id': 'a', 'wait': '5'}),
            ('get_answer', {}),
            ('get_discussion', {'id': '.'}),
            ('archive_note', {'id': 5}),
            ('complete_todo', {}),
        ]
        for tool, args in cases:
            with self.subTest(tool=tool, args=str(args)[:120]):
                out, calls, _ = call(tool, args)
                self.assertIn('error', out)
                self.assertNotIn('status', out)
                self.assertEqual(calls, [])

    def test_limit_semantics(self):
        for tool in ('list_notes', 'list_discussions'):
            for limit in (0, -3, 1, 50, 500):
                with self.subTest(tool=tool, limit=limit):
                    _, calls, _ = call(tool, {'limit': limit})
                    self.assertEqual(parse_qs(urlsplit(calls[0][0].full_url).query), {'limit': [str(limit)]})
            for limit in (True, False, '5', 2.5, [1]):
                with self.subTest(tool=tool, limit=limit):
                    out, calls, _ = call(tool, {'limit': limit})
                    self.assertIn('error', out)
                    self.assertEqual(calls, [])
            _, calls, _ = call(tool, {'limit': None})
            self.assertEqual(urlsplit(calls[0][0].full_url).query, '')
        for limit in (5, None, 0):
            with self.subTest(todo_limit=limit):
                out, calls, _ = call('list_todos', {'limit': limit})
                self.assertEqual(out, {'error': 'list_todos does not accept limit'})
                self.assertEqual(calls, [])

    def test_note_request_size_limit(self):
        limit = 8 * 1024 * 1024
        out, calls, _ = call('create_note', {'title': 't', 'body': 'x' * limit})
        self.assertIn('error', out)
        self.assertEqual(calls, [])
        out, calls, _ = call('update_note', {'id': 'n', 'body': 'x' * limit, 'if_match': 'e'})
        self.assertIn('error', out)
        self.assertEqual(calls, [])
        out, calls, _ = call('create_note', {'title': 't', 'body': 'x' * (limit - 1024)})
        self.assertNotIn('error', out)
        self.assertEqual(len(calls), 1)

    def test_header_errors_make_no_request(self):
        bad = ['', 'x' * 256, 5, 'caf\u00e9', 'a\tb', 'a\x7fb', 'line\nbreak', ['k']]
        for tool, args in [('create_note', {'title': 'x'}), ('append_note', {'id': 'n', 'body': 'x'}), ('create_todo', {'text': 'x'})]:
            for value in bad:
                with self.subTest(tool=tool, value=repr(value)[:20]):
                    out, calls, _ = call(tool, {**args, 'idempotency_key': value})
                    self.assertIn('error', out)
                    self.assertEqual(calls, [])
            _, calls, _ = call(tool, {**args, 'idempotency_key': 'x' * 255})
            self.assertEqual(calls[0][0].get_header('Idempotency-key'), 'x' * 255)
            _, calls, _ = call(tool, {**args, 'idempotency_key': None})
            self.assertIsNone(calls[0][0].get_header('Idempotency-key'))
        for value in bad:
            with self.subTest(if_match=repr(value)[:20]):
                out, calls, _ = call('update_note', {'id': 'n', 'body': 'x', 'if_match': value})
                self.assertIn('error', out)
                self.assertEqual(calls, [])

    def test_http_errors_expose_only_safe_machine_fields(self):
        correlation = 'c0ffee-4bf92f3577b34da6'
        for status, code in [(401, 'invalid_key'), (403, 'insufficient_scope'), (409, 'note_live_busy'), (412, 'etag_mismatch'), (428, 'if_match_required'), (429, 'rate_limited'), (503, 'api_writes_disabled')]:
            with self.subTest(status=status):
                body = json.dumps({'type': 'about:blank', 'title': 'human text ' + KEY, 'detail': KEY, 'instance': '/v1/notes', 'code': code, 'correlation_id': correlation, 'required_scope': 'notes:write'}).encode()
                exc = HTTPError(BASE, status, 'x', {'Retry-After': '7', 'X-Other': KEY}, io.BytesIO(body))
                out, calls, _ = call('create_note', {'title': 't'}, failure=exc)
                self.assertEqual(out, {'error': 'Inkling API request failed', 'status': status, 'retry_after': '7', 'code': code, 'correlation_id': correlation})
                self.assertNotIn(KEY, json.dumps(out))
                self.assertEqual(len(calls), 1)

    def test_http_error_member_redaction_and_bounds(self):
        cases = [
            ({'code': KEY.upper(), 'correlation_id': 'X-' + KEY.upper()}, {}),
            ({'code': 'Bad Code', 'correlation_id': 'has space'}, {}),
            ({'code': 5, 'correlation_id': ['a']}, {}),
            ({'code': 'a' * 65, 'correlation_id': 'a' * 129}, {}),
            ({'code': 'a' * 64, 'correlation_id': 'a' * 128}, {'code': 'a' * 64, 'correlation_id': 'a' * 128}),
            ({'code': '', 'correlation_id': ''}, {}),
            ({'correlation_id': 'X-' + KEY.upper(), 'code': 'ok_code'}, {'code': 'ok_code'}),
            ([{'code': 'ok_code'}], {}),
            ('plain', {}),
        ]
        for member, expected in cases:
            with self.subTest(member=str(member)[:40]):
                exc = HTTPError(BASE, 400, 'x', {}, io.BytesIO(json.dumps(member).encode()))
                out, _, _ = call('usage', failure=exc)
                self.assertEqual(out, {'error': 'Inkling API request failed', 'status': 400, **expected})
        for retry in ('abc', '-1', '1.5', '12345678901', KEY, ''):
            with self.subTest(retry=retry):
                exc = HTTPError(BASE, 429, 'x', {'Retry-After': retry}, io.BytesIO(b'{}'))
                out, _, _ = call('usage', failure=exc)
                self.assertNotIn('retry_after', out)
                self.assertNotIn(KEY, json.dumps(out))

    def test_http_error_non_json_oversized_and_unreadable_bodies(self):
        for raw in (b'', b'<html>' + KEY.encode() + b'</html>', b'\xff\xfe', b'{"code":', b'[' * 5000):
            with self.subTest(raw=raw[:12]):
                exc = HTTPError(BASE, 503, 'x', {}, io.BytesIO(raw))
                out, calls, _ = call('usage', failure=exc)
                self.assertEqual(out, {'error': 'Inkling API request failed', 'status': 503})
                self.assertEqual(len(calls), 1)
        huge = b'{"code":"invalid_request","pad":"' + b'x' * 20000 + b'"}'
        stream = CountingStream(huge)
        out, _, _ = call('usage', failure=HTTPError(BASE, 400, 'x', {}, stream))
        self.assertEqual(out, {'error': 'Inkling API request failed', 'status': 400})
        self.assertEqual(stream.consumed, 16385)
        out, _, _ = call('usage', failure=HTTPError(BASE, 500, 'x', {}, None))
        self.assertEqual(out, {'error': 'Inkling API request failed', 'status': 500})

    def test_mutations_are_never_retried(self):
        for tool in ('create_note', 'append_note', 'create_todo', 'complete_todo', 'archive_note', 'update_note'):
            with self.subTest(tool=tool):
                exc = HTTPError(BASE, 503, 'x', {'Retry-After': '1'}, io.BytesIO(b'{"code":"unavailable"}'))
                out, calls, _ = call(tool, {**FULL_ARGS[tool]}, failure=exc)
                self.assertEqual(out['code'], 'unavailable')
                self.assertEqual(len(calls), 1)

    def test_invalid_or_empty_success_bodies_are_safe(self):
        for raw in (b'<html>' + KEY.encode() + b'</html>', b'\xff\xfe', b'{"a":'):
            with self.subTest(raw=raw[:10]):
                out, calls, _ = call('usage', response=raw)
                self.assertEqual(out, {'error': 'Inkling API request failed'})
                self.assertEqual(len(calls), 1)
        out, calls, _ = call('usage', response=b'')
        self.assertIsNone(out)
        for payload in ([], 'text', 5):
            out, _, _ = call('usage', response=json.dumps(payload).encode())
            self.assertEqual(out, payload)

    def test_unknown_tools_and_missing_credentials(self):
        for tool in ('nope', 'inkling.usage', '', 'usage '):
            with self.subTest(tool=tool):
                out, calls, _ = call(tool, {})
                self.assertEqual(out, {'error': 'Unknown Inkling tool'})
                self.assertEqual(calls, [])
        for key in ('', None, 5):
            with self.subTest(key=key):
                out, calls, _ = call('usage', key=key)
                self.assertIn('Missing Inkling credential', out['error'])
                self.assertEqual(calls, [])
        output = io.StringIO()
        with patch('urllib.request.build_opener') as factory, contextlib.redirect_stdout(output):
            runpy.run_path(str(MAIN), init_globals={'params': {'tool': 'inkling.usage'}})
        self.assertIn('Missing Inkling credential', json.loads(output.getvalue())['error'])
        factory.assert_not_called()

    def test_key_is_never_echoed_in_local_errors(self):
        out, _, _ = call('create_note', {'title': KEY, 'tags': [KEY + '#'], 'idempotency_key': KEY})
        self.assertNotIn(KEY, json.dumps(out))


if __name__ == '__main__':
    unittest.main()
