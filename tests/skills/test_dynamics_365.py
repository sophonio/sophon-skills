"""Offline mock-HTTP integration tests for the dynamics-365 skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

TENANT = "11111111-aaaa-bbbb-cccc-222222222222"
CID = "33333333-dddd-eeee-ffff-444444444444"
SECRET = "s3cr3t-CLIENT-SECRET-value"
ENV = "https://org12345.crm.dynamics.com"
API = f"{ENV}/api/data/v9.2"
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
TOK = "eyJ-access-token"
GUID = "3f2504e0-4f89-41d3-9a0c-0305e82c3301"
PREFER = 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'

EXPECTED_TOKEN_BODY = (
    "grant_type=client_credentials"
    f"&client_id={CID}"
    "&client_secret=s3cr3t-CLIENT-SECRET-value"
    "&scope=https%3A%2F%2Forg12345.crm.dynamics.com%2F.default"
)


def creds(**extra):
    p = {"tenantId": TENANT, "clientId": CID, "clientSecret": SECRET, "environmentUrl": ENV}
    p.update(extra)
    return p


def tok():
    return resp(200, body={"access_token": TOK})


ok = True

# ---------------------------------------------------------------------------
# 1. dynamics.whoami — token-flow auth exactness + happy path
# ---------------------------------------------------------------------------
print("scenario: whoami happy path / token-flow exactness")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.whoami"), [
    tok(),
    resp(200, body={"@odata.context": f"{API}/$metadata#Microsoft.Dynamics.CRM.WhoAmIResponse",
                    "BusinessUnitId": "bu-guid", "UserId": "user-guid",
                    "OrganizationId": "org-guid"}),
])
ok &= check("two requests (token + API)", len(ex) == 2, repr(ex))
ok &= check("token URL byte-exact", ex[0].url == TOKEN_URL, ex[0].url)
ok &= check("token method POST", ex[0].method == "POST", ex[0].method)
ok &= check("token body byte-exact (Dataverse scope, NOT Graph)",
            ex[0].body == EXPECTED_TOKEN_BODY, str(ex[0].body))
ok &= check("token content-type form-urlencoded",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
ok &= check("token user-agent", ex[0].headers.get("user-agent") == "sophon-dynamics-365-skill",
            str(ex[0].headers))
ok &= check("WhoAmI URL byte-exact", ex[1].url == f"{API}/WhoAmI", ex[1].url)
ok &= check("Bearer auth on API call", ex[1].headers.get("authorization") == f"Bearer {TOK}",
            str(ex[1].headers))
ok &= check("OData-Version 4.0", ex[1].headers.get("odata-version") == "4.0", str(ex[1].headers))
ok &= check("OData-MaxVersion 4.0", ex[1].headers.get("odata-maxversion") == "4.0",
            str(ex[1].headers))
ok &= check("Accept application/json", ex[1].headers.get("accept") == "application/json",
            str(ex[1].headers))
ok &= check("read carries formatted-value Prefer header",
            ex[1].headers.get("prefer") == PREFER, str(ex[1].headers))
ok &= check("output shaped to userId/businessUnitId/organizationId",
            out == {"userId": "user-guid", "businessUnitId": "bu-guid",
                    "organizationId": "org-guid"}, str(out))
ok &= check("secret not echoed", SECRET not in json.dumps(out))

# ---------------------------------------------------------------------------
# 2. dynamics.query_records — happy path, formatted values alongside raw
# ---------------------------------------------------------------------------
print("scenario: query_records happy path / response shaping")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.query_records", entitySet="accounts",
                                         select="name,revenue", filter="revenue gt 100000",
                                         orderby="name asc", top=10), [
    tok(),
    resp(200, body={"@odata.context": "ctx", "value": [
        {"@odata.etag": 'W/"123"', "name": "Contoso", "revenue": 1000000.0,
         "revenue@OData.Community.Display.V1.FormattedValue": "$1,000,000.00",
         "_primarycontactid_value": "c-guid",
         "_primarycontactid_value@OData.Community.Display.V1.FormattedValue": "Jane Doe",
         "_primarycontactid_value@Microsoft.Dynamics.CRM.lookuplogicalname": "contact",
         "accountid": GUID},
    ]}),
])
ok &= check("query URL byte-exact ($select/$filter/$orderby/$top)",
            ex[1].url == f"{API}/accounts?%24select=name%2Crevenue"
                         "&%24filter=revenue+gt+100000&%24orderby=name+asc&%24top=10",
            ex[1].url)
ok &= check("read Prefer header on query", ex[1].headers.get("prefer") == PREFER,
            str(ex[1].headers))
ok &= check("count == 1", out.get("count") == 1, str(out)[:300])
rec = out["records"][0]
ok &= check("raw values kept", rec.get("name") == "Contoso" and rec.get("revenue") == 1000000.0
            and rec.get("_primarycontactid_value") == "c-guid", str(rec))
ok &= check("formatted values alongside raw as <field>@formatted",
            rec.get("revenue@formatted") == "$1,000,000.00"
            and rec.get("_primarycontactid_value@formatted") == "Jane Doe", str(rec))
ok &= check("etag and non-formatted annotations dropped",
            "@odata.etag" not in rec
            and "_primarycontactid_value@Microsoft.Dynamics.CRM.lookuplogicalname" not in rec,
            str(rec))

# top clamped to 50
print("scenario: query_records clamps top to 50")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.query_records", entitySet="contacts",
                                         top=5000), [
    tok(),
    resp(200, body={"value": []}),
])
ok &= check("top clamped to 50 in URL", ex[1].url == f"{API}/contacts?%24top=50", ex[1].url)
ok &= check("empty count 0", out == {"count": 0, "records": []}, str(out))

# ---------------------------------------------------------------------------
# 3. dynamics.query_records — @odata.nextLink pagination (same host only)
# ---------------------------------------------------------------------------
print("scenario: query_records follows @odata.nextLink up to top cap")
NEXT = f"{API}/contacts?%24top=3&%24skiptoken=%3Ccookie%20page%3D%221%22%3E"
out, ex = run_tool("dynamics-365", creds(tool="dynamics.query_records", entitySet="contacts",
                                         top=3), [
    tok(),
    resp(200, body={"value": [{"fullname": "A"}, {"fullname": "B"}],
                    "@odata.nextLink": NEXT}),
    resp(200, body={"value": [{"fullname": "C"}, {"fullname": "D"}]}),  # over-delivers, no next
])
ok &= check("three requests (token + 2 pages)", len(ex) == 3, repr(ex))
ok &= check("first page URL", ex[1].url == f"{API}/contacts?%24top=3", ex[1].url)
ok &= check("second page hits nextLink verbatim", ex[2].url == NEXT, ex[2].url)
ok &= check("second page still authed + Prefer",
            ex[2].headers.get("authorization") == f"Bearer {TOK}"
            and ex[2].headers.get("prefer") == PREFER, str(ex[2].headers))
ok &= check("cap enforced: count == 3", out.get("count") == 3, str(out))
ok &= check("records trimmed to cap", [r["fullname"] for r in out["records"]] == ["A", "B", "C"],
            str(out))

print("scenario: query_records stops at the page cap on an endless nextLink chain")


def looping_page(n):
    return resp(200, body={"value": [{"fullname": f"P{n}"}],
                           "@odata.nextLink": f"{API}/contacts?%24skiptoken=p{n + 1}"})


out, ex = run_tool("dynamics-365", creds(tool="dynamics.query_records", entitySet="contacts",
                                         top=50),
                   [tok()] + [looping_page(n) for n in range(1, 7)],
                   expect_all_consumed=False)
ok &= check("page cap: exactly 6 requests (token + 5 pages)", len(ex) == 6, repr(ex))
ok &= check("page cap: 5 under-delivered records returned", out.get("count") == 5
            and [r["fullname"] for r in out["records"]] == ["P1", "P2", "P3", "P4", "P5"],
            str(out))

print("scenario: query_records never follows a nextLink off the environment host")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.query_records", entitySet="contacts",
                                         top=10), [
    tok(),
    resp(200, body={"value": [{"fullname": "A"}],
                    "@odata.nextLink": "https://evil.example.com/api/data/v9.2/contacts?p=2"}),
])
ok &= check("foreign-host nextLink not followed (token + 1 page only)", len(ex) == 2, repr(ex))
ok &= check("returns first page only", out.get("count") == 1, str(out))

# ---------------------------------------------------------------------------
# 4. dynamics.get_record — happy path + GUID validation
# ---------------------------------------------------------------------------
print("scenario: get_record happy path")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.get_record", entitySet="accounts",
                                         recordId=GUID, select="name,statecode"), [
    tok(),
    resp(200, body={"@odata.context": "ctx", "@odata.etag": 'W/"9"',
                    "name": "Contoso", "statecode": 0,
                    "statecode@OData.Community.Display.V1.FormattedValue": "Active",
                    "accountid": GUID}),
])
ok &= check("URL byte-exact", ex[1].url == f"{API}/accounts({GUID})?%24select=name%2Cstatecode",
            ex[1].url)
ok &= check("record shaped (raw + formatted, annotations dropped)",
            out == {"name": "Contoso", "statecode": 0, "statecode@formatted": "Active",
                    "accountid": GUID}, str(out))

print("scenario: get_record rejects a non-GUID recordId, no HTTP")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.get_record", entitySet="accounts",
                                         recordId="abc/../def?x=1"), [])
ok &= check("invalid GUID rejected", "error" in out and "recordId" in out["error"], str(out))
ok &= check("no HTTP request made (not even token)", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 5. dynamics.list_entity_fields — happy path
# ---------------------------------------------------------------------------
print("scenario: list_entity_fields happy path")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.list_entity_fields", entity="account"), [
    tok(),
    resp(200, body={"value": [
        {"LogicalName": "name", "AttributeType": "String", "MetadataId": "m1",
         "DisplayName": {"UserLocalizedLabel": {"Label": "Account Name"},
                         "LocalizedLabels": [{"Label": "Account Name"}]}},
        {"LogicalName": "revenue", "AttributeType": "Money", "MetadataId": "m2",
         "DisplayName": {"UserLocalizedLabel": None}},
    ]}),
])
ok &= check("URL byte-exact (EntityDefinitions + IsValidForRead filter)",
            ex[1].url == f"{API}/EntityDefinitions(LogicalName='account')/Attributes"
                         "?%24select=LogicalName%2CAttributeType%2CDisplayName"
                         "&%24filter=IsValidForRead+eq+true",
            ex[1].url)
ok &= check("fields trimmed for query construction",
            out == {"count": 2, "fields": [
                {"logicalName": "name", "type": "String", "displayName": "Account Name"},
                {"logicalName": "revenue", "type": "Money", "displayName": None}]},
            str(out))

# ---------------------------------------------------------------------------
# 6. WRITE PATHS — create_record (204 + OData-EntityId), update_record, add_annotation
# ---------------------------------------------------------------------------
print("scenario: create_record posts body, reads id from OData-EntityId header")
FIELDS = {"name": "Contoso Ltd", "revenue": 250000,
          "primarycontactid@odata.bind": f"/contacts({GUID})", "industrycode": 6}
out, ex = run_tool("dynamics-365", creds(tool="dynamics.create_record", entitySet="accounts",
                                         fields=FIELDS), [
    tok(),
    resp(204, headers={"OData-EntityId": f"{API}/accounts({GUID})"}),
])
ok &= check("method POST", ex[1].method == "POST", ex[1].method)
ok &= check("URL byte-exact", ex[1].url == f"{API}/accounts", ex[1].url)
ok &= check("JSON body matches fields (incl. @odata.bind lookup + int option-set)",
            ex[1].json == FIELDS, str(ex[1].body))
ok &= check("content-type json", ex[1].headers.get("content-type") == "application/json",
            str(ex[1].headers))
ok &= check("no formatted Prefer header on write", "prefer" not in ex[1].headers,
            str(ex[1].headers))
ok &= check("id extracted from OData-EntityId",
            out == {"id": GUID, "entitySet": "accounts", "created": True}, str(out))

print("scenario: create_record with no OData-EntityId header errors instead of id: null")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.create_record", entitySet="accounts",
                                         fields={"name": "X"}), [
    tok(),
    resp(204),
])
ok &= check("missing OData-EntityId surfaces an error, not created:true",
            "OData-EntityId" in out.get("error", "") and "created" not in out, str(out))

print("scenario: update_record PATCHes with If-Match: *")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.update_record", entitySet="accounts",
                                         recordId=GUID, fields={"name": "New Name"}), [
    tok(),
    resp(204),
])
ok &= check("method PATCH", ex[1].method == "PATCH", ex[1].method)
ok &= check("URL byte-exact", ex[1].url == f"{API}/accounts({GUID})", ex[1].url)
ok &= check("If-Match: * prevents upsert-as-create", ex[1].headers.get("if-match") == "*",
            str(ex[1].headers))
ok &= check("body is the fields object", ex[1].json == {"name": "New Name"}, str(ex[1].body))
ok &= check("success output", out == {"id": GUID, "entitySet": "accounts", "updated": True},
            str(out))

print("scenario: add_annotation binds objectid_<entity> to /<entitySet>(guid)")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.add_annotation", entitySet="accounts",
                                         recordId=GUID, noteText="Renewal call Friday",
                                         subject="Renewal"), [
    tok(),
    resp(204, headers={"OData-EntityId": f"{API}/annotations({GUID})"}),
])
ok &= check("POST /annotations", ex[1].method == "POST" and ex[1].url == f"{API}/annotations",
            f"{ex[1].method} {ex[1].url}")
ok &= check("annotation body (notetext/subject/objectid bind, singularized entity)",
            ex[1].json == {"notetext": "Renewal call Friday", "subject": "Renewal",
                           f"objectid_account@odata.bind": f"/accounts({GUID})"},
            str(ex[1].body))
ok &= check("annotation id returned",
            out == {"annotationId": GUID, "entitySet": "accounts", "recordId": GUID,
                    "created": True}, str(out))

print("scenario: add_annotation honors explicit entityLogicalName override")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.add_annotation",
                                         entitySet="opportunities", recordId=GUID,
                                         noteText="n", entityLogicalName="opportunity"), [
    tok(),
    resp(204, headers={"OData-EntityId": f"{API}/annotations({GUID})"}),
])
ok &= check("override used in bind property",
            f"objectid_opportunity@odata.bind" in (ex[1].json or {}), str(ex[1].body))

# ---------------------------------------------------------------------------
# 7. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 on the API surfaces a friendly error")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.whoami"), [
    tok(),
    err(401, body={"error": {"code": "0x80072560",
                             "message": "The user is not a member of the organization."}}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes API message",
            "not a member of the organization" in out["error"], out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw[:300])
ok &= check("secret not leaked in error output", SECRET not in raw, raw[:300])

print("scenario: token failure (bad secret) is friendly, secret absent")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.whoami"), [
    err(401, body={"error": "invalid_client",
                   "error_description": "AADSTS7000215: Invalid client secret provided."}),
])
raw = json.dumps(out)
ok &= check("token failure surfaced with status",
            "Token request failed (401)" in out.get("error", ""), str(out))
ok &= check("AADSTS description included", "AADSTS7000215" in out["error"], out["error"])
ok &= check("secret value absent from token error", SECRET not in raw, raw[:300])

print("scenario: 429 service-protection includes Retry-After")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.query_records", entitySet="accounts"), [
    tok(),
    err(429, body={"error": {"code": "0x80072322",
                             "message": "Number of requests exceeded the limit of 6000."}},
        headers={"Retry-After": "27"}),
])
ok &= check("429 surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("Retry-After seconds included", "Retry-After: 27s" in out["error"],
            out.get("error", ""))
ok &= check("service message included", "exceeded the limit" in out["error"],
            out.get("error", ""))

print("scenario: non-JSON error body tolerated")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.whoami"), [
    tok(),
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out)[:300])

print("scenario: missing required param -> friendly error, no HTTP call")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.query_records"), [])
ok &= check("entitySet required error", out.get("error") == "entitySet required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("dynamics-365", creds(tool="dynamics.create_record", entitySet="accounts"), [])
ok &= check("fields object required error",
            "fields object required" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: missing credentials -> connect-first error, no HTTP call")
out, ex = run_tool("dynamics-365", {"tool": "dynamics.whoami"}, [])
ok &= check("connect-first message names the fields",
            "connect the Dynamics 365 integration first" in out.get("error", "")
            and "environmentUrl" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: dynamics.nope", str(out))

# ---------------------------------------------------------------------------
# 8. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-injection entitySet is rejected, no HTTP")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.query_records",
                                         entitySet="abc/../def?x=1"), [])
ok &= check("evil entitySet rejected",
            "error" in out and "Invalid entitySet" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: dot segments in entitySet rejected")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.query_records", entitySet=".."), [])
ok &= check("'..' entitySet rejected", "Invalid entitySet" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: path-injection entity name on list_entity_fields rejected")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.list_entity_fields",
                                         entity="account')/Attributes?evil="), [])
ok &= check("evil entity rejected", "Invalid entity" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: path-injection recordId on writes rejected")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.update_record", entitySet="accounts",
                                         recordId="abc/../def?x=1", fields={"name": "x"}), [])
ok &= check("evil recordId rejected on update", "Invalid recordId" in out.get("error", ""),
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("dynamics-365", creds(tool="dynamics.add_annotation", entitySet="accounts",
                                         recordId="abc/../def?x=1", noteText="n"), [])
ok &= check("evil recordId rejected on annotation", "Invalid recordId" in out.get("error", ""),
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("dynamics-365", creds(tool="dynamics.get_record", entitySet="accounts",
                                         recordId=GUID), [
    tok(),
    err(403, body={"error": {"message": "Principal user is missing prvReadAccount privilege"}}),
])
ok &= check("clientSecret absent from 403 error output", SECRET not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
