from playwright.sync_api import sync_playwright
import json, os, time

OUT = "reports/agent2a/playwright/id_scan"
os.makedirs(OUT, exist_ok=True)

def write_result(results):
    with open(os.path.join(OUT, "id_scan_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

def main():
    ids_path = "tests/playwright/ids_registry.json"
    if not os.path.exists(ids_path):
        write_result({"error": "missing ids_registry.json"})
        print("missing ids_registry.json")
        return
    try:
        ids_raw = json.load(open(ids_path))
    except Exception as e:
        write_result({"error": f"failed to load ids_registry.json: {e}"})
        print("failed to load ids_registry.json")
        return

    results = []
    base = os.environ.get("ADMIN_BASE", "http://127.0.0.1:8029")

    try:
        with sync_playwright() as p:
            # use headless=False to run a visible browser when available
            browser = p.chromium.launch(headless=False)
            ctx = browser.new_context()
            page = ctx.new_page()
            try:
                page.goto(base, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                # still proceed; some pages will load after interactions
                results.append({"error": f"failed to load base page: {e}"})

            # ids_raw could be dict or list
            entries = []
            if isinstance(ids_raw, dict):
                for k,v in ids_raw.items():
                    if isinstance(v, list):
                        for item in v:
                            entries.append({"tab": k, "id": item})
                    else:
                        entries.append({"tab": k, "id": v})
            elif isinstance(ids_raw, list):
                entries = ids_raw
            else:
                write_result({"error": "unsupported ids_registry.json format"})
                return

            for entry in entries:
                tab = entry.get("tab")
                elid = entry.get("id")
                record = {"id": elid, "tab": tab, "found": False}
                try:
                    # try to activate tab by [data-tab] or visible text link
                    if tab:
                        try:
                            el = page.query_selector(f"[data-tab='{tab}']")
                            if el:
                                try:
                                    page.click(f"[data-tab='{tab}']", timeout=2000)
                                except:
                                    pass
                            else:
                                try:
                                    page.click(f"text=\"{tab}\"", timeout=2000)
                                except:
                                    pass
                        except Exception:
                            pass
                    time.sleep(0.5)
                    sel = f"#{elid}"
                    node = page.query_selector(sel)
                    if node:
                        record["found"] = True
                        # try to screenshot element
                        try:
                            bbox = node.bounding_box()
                            snap = os.path.join(OUT, f"{elid}_snap.png")
                            if bbox:
                                page.screenshot(path=snap, clip=bbox)
                            else:
                                page.screenshot(path=snap)
                            record["snapshot"] = snap
                        except Exception as e:
                            # fallback to full page screenshot
                            try:
                                snap = os.path.join(OUT, f"{elid}_snap.png")
                                page.screenshot(path=snap)
                                record["snapshot"] = snap
                            except Exception as e2:
                                record["screenshot_error"] = str(e2)
                        try:
                            dom_snip = node.inner_html()
                            with open(os.path.join(OUT, f"{elid}_dom.html"), "w", encoding="utf-8") as f:
                                f.write(dom_snip)
                            record["dom"] = os.path.join(OUT, f"{elid}_dom.html")
                        except Exception as e:
                            record["dom_error"] = str(e)
                    results.append(record)
                except Exception as e:
                    results.append({"id": elid, "tab": tab, "found": False, "error": str(e)})

            try:
                browser.close()
            except:
                pass

    except Exception as e:
        # Playwright not available or browser failed to launch
        write_result({"error": f"playwright-run-failed: {e}"})
        print("playwright-run-failed")
        return

    write_result(results)
    print("id scan complete, results in", OUT)

if __name__ == '__main__':
    main()
