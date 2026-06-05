from pathlib import Path
from datetime import datetime
from google import genai
import subprocess
import sys

import config

api_key = config.get_api_key()

if not api_key:
    print(config.NO_API_KEY_MSG)
    sys.exit(1)

client = genai.Client(api_key=api_key)

conversation_path = Path("conversation.txt")
inbox_path = Path(".data/inbox/memories_to_review.md")

inbox_path.parent.mkdir(parents=True, exist_ok=True)

conversation = conversation_path.read_text(encoding="utf-8")

prompt = f"""
You are the memory module of a personal AI assistant.

Analyze this conversation and extract only the information worth remembering
long-term.

Keep:
- the user's projects
- goals
- work preferences
- tools they use
- important decisions
- durable knowledge
- useful tasks

Ignore:
- filler
- thanks and pleasantries
- hesitations
- repetitions
- temporary details with no lasting value

Tag EACH memory with exactly one category in square brackets, chosen from:
  [Identity]   who the user is: name, age, location, job, studies, personality, hobbies, interests
  [Projects]   something the user is building or developing, with a goal or deadline
  [Ideas]      a decision, choice, opinion, plan or strategy the user holds or is weighing
  [Learnings]  a concept, lesson, technical explanation or fact the user learned
  [Tools]      an existing software, language, framework, service or device the user uses
  [Habits]     a personal trait, strength, weakness or behavior pattern of the user
  [Sources]    an external link, article, book, video or doc to read or revisit
Use [Unsorted] ONLY if none of the above clearly fit.

Write each memory as a third-person statement about the user. Return clean
Markdown for Obsidian only, in exactly this format:

# Memories to review

Date: {datetime.now().strftime("%Y-%m-%d")}

## High confidence

- [ ] [Tools] The user codes daily in Neovim and tmux.
- [ ] [Identity] ...

## To verify

- [ ] [Category] ...

## Low priority

- [ ] [Category] ...

Conversation:
{conversation}
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

result = response.text

inbox_path.write_text(result, encoding="utf-8")

print("Extraction complete → .data/inbox/memories_to_review.md")
print("Running automatic review…")

# Automatic review — zero interaction, zero extra API call
auto_review = Path(__file__).parent / "memory_auto_review.py"
proc = subprocess.run(
    [sys.executable, str(auto_review)],
    capture_output=False,   # stream logs in real time
    text=True,
)

if proc.returncode != 0:
    print("Warning: automatic review failed (check memory_auto_review.py).")
else:
    print("\nMemories saved to your Obsidian vault (Memories/ + Categories/).")
    print("Readable log: .data/inbox/last_run.md")
