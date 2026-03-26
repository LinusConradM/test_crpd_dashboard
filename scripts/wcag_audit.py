import asyncio
import json

from axe_playwright_python.async_playwright import Axe
from playwright.async_api import async_playwright


async def run_audit():
    print("Starting WCAG Audit of CRPD Dashboard...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        print("Navigating to http://localhost:8502...")
        try:
            await page.goto("http://localhost:8502", timeout=10000)
            await page.wait_for_selector(".stApp", state="visible", timeout=10000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Failed to connect to the dashboard:\n{e}")
            await browser.close()
            return

        print("Running Axe-core analysis (WCAG 2.2 AA)...")
        axe = Axe()
        results = await axe.run(
            page,
            options={
                "runOnly": {
                    "type": "tag",
                    "values": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
                }
            },
        )

        # AxeResults in python wrapper uses the generate_report method or raw_results
        violations = []
        if hasattr(results, "violations"):
            violations = results.violations
        elif hasattr(results, "generate_report"):
            # fallback if it's the older API
            report_str = results.generate_report()
            print(report_str)
        elif hasattr(results, "to_dict"):
            violations = results.to_dict().get("violations", [])

        # Let's inspect what attributes are actually on the object to be safe:
        print("\nAttributes on AxeResults object:")
        print(dir(results))

        report = []

        # If we successfully managed to extract violations as a list/dict
        if isinstance(violations, list) and len(violations) > 0 and isinstance(violations[0], dict):
            print(f"\nAudit Complete! Found {len(violations)} distinct violation types.\n")
            for v in violations:
                item = {
                    "Description": v.get("description", ""),
                    "Impact": v.get("impact", ""),
                    "Help": v.get("help", ""),
                    "Help URL": v.get("helpUrl", ""),
                    "Nodes Affected": len(v.get("nodes", [])),
                    "Tags": v.get("tags", []),
                }
                report.append(item)

                print(f"[{item['Impact'].upper()}] {item['Help']}")
                print(f"  - Description: {item['Description']}")
                print(f"  - Nodes affected: {item['Nodes Affected']}")
                print(f"  - Guidelines: {', '.join(item['Tags'])}")
                print("-" * 50)

            # Save to file
            with open("Dashboard Documents/WCAG_Automated_Audit_Report.json", "w") as f:
                json.dump(report, f, indent=4)

            print(
                "\nDetailed JSON report saved to: Dashboard Documents/WCAG_Automated_Audit_Report.json"
            )
        else:
            print(
                "\nCould not automatically parse violation dict. Generating Markdown report instead:"
            )
            if hasattr(results, "generate_report"):
                res = results.generate_report()

                md_content = "---\n"
                md_content += 'title: "WCAG 2.2 Automated Audit Report"\n'
                md_content += 'subtitle: "CRPD Disability Rights Data Dashboard"\n'
                md_content += 'author: "Automated Accessibility Scanner (Playwright + Axe-core)"\n'
                md_content += "format:\n"
                md_content += "  html:\n"
                md_content += "    theme: cosmo\n"
                md_content += "    toc: true\n"
                md_content += "    toc-depth: 3\n"
                md_content += '    toc-title: "Table of Contents"\n'
                md_content += "    number-sections: true\n"
                md_content += "    smooth-scroll: true\n"
                md_content += "    css: styles.css\n"
                md_content += "---\n\n"
                md_content += "# WCAG 2.2 Automated Audit Report\n\n"
                md_content += "This report was automatically generated using Playwright and Axe-core, analyzing the running CRPD Dashboard against WCAG 2.2 AA standards.\n\n"

                # Basic parsing to make it nice markdown
                blocks = res.split("Rule Violated:\n")
                if len(blocks) > 0:
                    md_content += f"**{blocks[0].strip()}**\n\n---\n\n"

                    for block in blocks[1:]:
                        lines = block.split("\n")
                        rule_name = lines[0].strip()
                        md_content += f"## {rule_name}\n\n"

                        in_messages = False
                        for line in lines[1:]:
                            stripped = line.strip()
                            if not stripped:
                                continue

                            if stripped.startswith("URL:"):
                                url = stripped.split("URL:")[1].strip()
                                md_content += f"- **Reference:** [{url}]({url})\n"
                            elif stripped.startswith("Impact Level:"):
                                md_content += f"- **Impact:** `{stripped.split('Impact Level:')[1].strip()}`\n"
                            elif stripped.startswith("Tags:"):
                                md_content += (
                                    f"- **Guidelines:** {stripped.split('Tags:')[1].strip()}\n"
                                )
                            elif stripped.startswith("Elements Affected:"):
                                md_content += "\n### Elements Affected\n"
                            elif stripped.startswith("1)\tTarget:") or stripped.startswith(
                                "Target:"
                            ):
                                md_content += (
                                    f"\n**Target Node:** `{stripped.split('Target:')[1].strip()}`\n"
                                )
                                in_messages = False
                            elif stripped.startswith("Snippet:"):
                                code = stripped.split("Snippet:")[1].strip()
                                md_content += f"\n**HTML Snippet:**\n```html\n{code}\n```\n"
                            elif stripped.startswith("Messages:"):
                                md_content += "\n**Failure Reasons:**\n"
                                in_messages = True
                            elif stripped.startswith("*"):
                                md_content += f"- {stripped[1:].strip()}\n"
                            else:
                                if in_messages:
                                    md_content += f"- {stripped}\n"
                                else:
                                    # Fallback
                                    md_content += f"{stripped}  \n"
                        md_content += "\n---\n\n"

                with open("Dashboard Documents/WCAG_Automated_Audit_Report.md", "w") as f:
                    f.write(md_content)

                print(
                    "Markdown report saved to: Dashboard Documents/WCAG_Automated_Audit_Report.md"
                )

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_audit())
