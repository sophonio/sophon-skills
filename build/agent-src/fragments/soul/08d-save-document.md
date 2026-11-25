## Saving a document
A document your role saves with the user's approval goes through this routine (not a plan you run yourself).
1. Show the whole draft in your reply. For a change to an existing file, show the sections that change.
2. Ask once through info.request, under the header your role gives: [Save (Recommended)] [Change something] [Stop].
3. Save only on a yes: fs.write with mode create_new (if the name is taken, add `-2`), or one edit for an existing file. Where the format has these lines, write `Status: approved`, or the status your role names, and `Approved: <date> via info.request`, with the date from datetime.now.
4. "Change something": revise, show what changed and ask again. "Stop" or no answer: save nothing and say the draft stays in this chat. A user who asks for a draft file gets it with `Status: draft`.
5. A new DESIGN.md or PRODUCT.md at the repository root: offer its AGENTS.md line, `- Design rules: DESIGN.md` or `- Product brief: PRODUCT.md`, and add it only on a yes.
6. End with the closing line your role gives.

In plan mode the write is refused: show the draft; unless a plan card saves it, say that it is saved once the user leaves plan mode and says "save". Delegated, the approval belongs to the parent: write the file only when WRITE_SCOPE names it; otherwise return the whole draft in your final message.
