import os
import sys


file_path = "src/tab_overview.py"
with open(file_path) as f:
    lines = f.readlines()

output_lines = []
indicator_block = []

state = "PRE"  # PRE, INDICATOR, POST
for line in lines:
    if line.strip() == "# Key Global CRPD Indicators":
        state = "INDICATOR"

    if state == "INDICATOR" and line.strip() == "# Key Insights Section":
        state = "POST"

    if state == "PRE":
        output_lines.append(line)
    elif state == "INDICATOR":
        indicator_block.append(line)
    elif state == "POST":
        output_lines.append(line)

# Let's find exactly where 'def render(df, df_all, ARTICLE_PRESETS):' is.
render_idx = -1
for i, line in enumerate(output_lines):
    if line.startswith("def render("):
        render_idx = i
        break

if render_idx == -1:
    print("Could not find render function.")
    sys.exit(1)

# we want to insert indicator_block right after def render(df, df_all, ARTICLE_PRESETS):
# but add a line break and a separator after it to cleanly separate from Understanding CRPD Implementation

new_lines = (
    output_lines[: render_idx + 1]
    + indicator_block
    + ['\n    st.markdown("---")\n']
    + output_lines[render_idx + 1 :]
)

with open(file_path, "w") as f:
    f.writelines(new_lines)

print("SUCCESS")
