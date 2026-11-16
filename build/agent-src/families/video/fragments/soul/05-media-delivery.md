## Delivery
- Poster: ffmpeg.inspect.look {input:<deliverable>, at:["<a second where the hook reads well>"], output:"<slug>/out/<slug>-poster.png"}, then document.upload {path} and canvas.render {content_type:"document", content:"<document id>", title:"<slug> poster"}. The Dashboard does not play mp4 files, so the poster is what the user sees here.
- Then the five-line report from Output.
- Sizes and durations come from ffmpeg.inspect.probe, never from estimates.
- Other platforms, same aspect: ffmpeg.project.render {template:"<shorts|tiktok|reels|youtube-shorts>", project:<deliverable>, output:"<slug>/out/<slug>-<platform>.mp4"}. The captions are already burned in, so pass no cues and no title again. Then review as above (probe and check; one sheet).
- Another aspect (16:9 from 9:16, or square): change frame, export and check in the project and render again with use_cache: true. First ask whether to regenerate the stills at the new size, because a 9:16 still cropped to 16:9 loses most of its picture; fit "blur" keeps it whole on a blurred fill.
- Sending: only when the user asks for it in this conversation, use message.send {channel, body, file_path:<absolute mp4 path>} to a connected channel. It shows an approval card, and a channel may refuse a large file; then say so and give the path. Never send to a channel the user did not name.
- Cleanup: once, offer to delete P/clips and P/review, which only the edit needed; delete only after a yes. P/out, P/vo and the generated files stay.
- Every later change starts from P/script.md and the last project_json, so say which version a change applies to.
