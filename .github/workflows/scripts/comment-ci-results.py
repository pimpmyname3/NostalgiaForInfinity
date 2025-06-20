import argparse
import json
import os
import pathlib
import pprint
import sys

import github
from github.GithubException import GithubException


def sort_report_names(value):
  if value == "Current":
    return -1
  if value == "Previous":
    return -2
  return -3


def delete_previous_comments(commit, created_comment_ids, exchanges):
  comment_starts = tuple({f"## {exchange.capitalize()}" for exchange in exchanges})
  for comment in commit.get_comments():
    if comment.user.login != "github-actions[bot]":
      # Not a comment made by this bot
      continue
    if comment.id in created_comment_ids:
      # These are the comments we have just created
      continue
    if not comment.body.startswith(comment_starts):
      # This comment does not start with our headers
      continue
    # We have a match, delete it
    print(f"Deleting previous comment {comment}")
    comment.delete()


def comment_results(options, results_data):
  gh = github.Github(os.environ["GITHUB_TOKEN"])
  repo = gh.get_repo(options.repo)
  print(f"Loaded Repository: {repo.full_name}", file=sys.stderr, flush=True)

  exchanges = set()
  comment_ids = set()
  commit = repo.get_commit(os.environ["GITHUB_SHA"])
  print(f"Loaded Commit: {commit}", file=sys.stderr, flush=True)

  for exchange in sorted(results_data):
    exchanges.add(exchange)
    sorted_report_names = list(reversed(sorted(results_data[exchange]["names"], key=sort_report_names)))
    for timerange in results_data[exchange]["timeranges"]:
      # Detect all trading modes with available data
      available_trading_modes = []
      trading_mode_outputs = {}

      for mt_candidate in ["spot", "futures"]:
        candidate_path = options.path / "current" / f"backtest-output-{exchange}-{mt_candidate}-{timerange}.txt"
        if candidate_path.exists():
          available_trading_modes.append(mt_candidate)
          trading_mode_outputs[mt_candidate] = candidate_path
          ft_output = candidate_path

      # Build the header
      if available_trading_modes:
        trading_mode_str = ", ".join(available_trading_modes)
        comment_body = f"## {exchange.capitalize()} ({trading_mode_str}) - {timerange}\n\n"
      else:
        comment_body = f"## {exchange.capitalize()} - {timerange}\n\n"

      report_table_header_1 = "| "
      report_table_header_2 = "| --: "
      for report_name in sorted_report_names:
        if report_name == "Current":
          report_table_header_1 += f"| {report_name} "
        else:
          report_table_header_1 += f"| [{report_name}](https://github.com/{options.repo}/commit/{results_data[exchange]['names'][report_name]}) "
        report_table_header_2 += "| --: "
      report_table_header_1 += "|\n"
      report_table_header_2 += "|\n"
      comment_body += report_table_header_1
      comment_body += report_table_header_2
      for key in sorted(results_data[exchange]["timeranges"][timerange]):
        row_line = "| "
        if key == "max_drawdown":
          label = "Max Drawdown"
          row_line += f" {label} |"
          for report_name in sorted_report_names:
            value = results_data[exchange]["timeranges"][timerange][key][report_name]
            if not isinstance(value, str):
              value = f"{round(value, 4)} %"
            row_line += f" {value} |"
          comment_body += f"{row_line}\n"
        elif key == "profit_mean_pct":
          label = "Profit Mean"
          row_line += f" {label} |"
          for report_name in sorted_report_names:
            value = results_data[exchange]["timeranges"][timerange][key][report_name]
            if not isinstance(value, str):
              value = f"{round(value, 4)} %"
            row_line += f" {value} |"
          comment_body += f"{row_line}\n"
        elif key == "profit_sum_pct":
          label = "Profit Sum"
          row_line += f" {label} |"
          for report_name in sorted_report_names:
            value = results_data[exchange]["timeranges"][timerange][key][report_name]
            if not isinstance(value, str):
              value = f"{round(value, 4)} %"
            row_line += f" {value} |"
          comment_body += f"{row_line}\n"
        elif key == "market_change":
          label = "Market Change"
          row_line += f" {label} |"
          for report_name in sorted_report_names:
            value = results_data[exchange]["timeranges"][timerange][key][report_name]
            if not isinstance(value, str):
              value = f"{round(value, 4)} %"
            row_line += f" {value} |"
          comment_body += f"{row_line}\n"
        elif key == "profit_total_pct":
          label = "Profit Total"
          row_line += f" {label} |"
          for report_name in sorted_report_names:
            value = results_data[exchange]["timeranges"][timerange][key][report_name]
            if not isinstance(value, str):
              value = f"{round(value, 4)} %"
            row_line += f" {value} |"
          comment_body += f"{row_line}\n"
        elif key == "winrate":
          label = "Win Rate"
          row_line += f" {label} |"
          for report_name in sorted_report_names:
            value = results_data[exchange]["timeranges"][timerange][key][report_name]
            if not isinstance(value, str):
              value = f"{round(value, 4)} %"
            row_line += f" {value} |"
          comment_body += f"{row_line}\n"
        else:
          if key == "duration_avg":
            label = "Average Duration"
          elif key == "trades":
            label = "Trades"
          else:
            label = key
          row_line += f" {label} |"
          for report_name in sorted_report_names:
            value = results_data[exchange]["timeranges"][timerange][key][report_name]
            row_line += f" {value} |"
          comment_body += f"{row_line}\n"
      ft_output = trading_mode_outputs[trading_mode]
      if ft_output:
        comment_body += "\n<details>\n"
        comment_body += "<summary>Detailed Backtest Output (click to see details)</summary>\n"
        try:
          comment_body += f"{ft_output.read_text().strip()}\n"
        except Exception as e:
          comment_body += f"⚠️ Failed to read file: {e}\n"
        comment_body += "</details>\n"
        comment_body += "\n\n"
      else:
        comment_body += "\n<details>\n"
        comment_body += "<summary>Detailed Backtest Output</summary>\n"
        comment_body += "⚠️ No backtest output file found for this exchange and timerange.\n"
        comment_body += "</details>\n"
      comment = commit.create_comment(comment_body.rstrip())
      print(f"Created Comment: {comment}", file=sys.stderr, flush=True)
      comment_ids.add(comment.id)

  delete_previous_comments(commit, comment_ids, exchanges)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--repo", required=True, help="The Organization Repository")
  parser.add_argument("path", metavar="PATH", type=pathlib.Path, help="Path where artifacts are extracted")

  if not os.environ.get("GITHUB_TOKEN"):
    parser.exit(status=1, message="GITHUB_TOKEN environment variable not set")

  options = parser.parse_args()

  if not options.path.is_dir():
    parser.exit(
      status=1,
      message=f"The directory where artifacts should have been extracted, {options.path}, does not exist",
    )

  reports_info_path = options.path / "reports-info.json"
  if not reports_info_path.exists():
    parser.exit(status=1, message=f"The {reports_info_path}, does not exist")

  reports_info = json.loads(reports_info_path.read_text())

  reports_data = {}
  for exchange in reports_info:
    reports_data[exchange] = {}
    timeranges = set()
    keys = set()

    # Load raw per-report results
    for trading_mode in reports_info[exchange]:
      if trading_mode not in reports_data[exchange]:
        reports_data[exchange][trading_mode] = {}

      for name in sorted(reports_info[exchange][trading_mode]):
        exchange_results = {}
        reports_data[exchange][trading_mode][name] = {
          "results": exchange_results,
          "sha": reports_info[exchange][trading_mode][name]["sha"],
        }

        results_path = pathlib.Path(reports_info[exchange][trading_mode][name]["path"])
        for results_file in results_path.rglob(f"ci-results-{exchange}-{trading_mode}-*"):
          # Load and merge results
          exchange_results.update(json.loads(results_file.read_text()))

        # Collect timeranges and keys
        for timerange in exchange_results:
          timeranges.add(timerange)
          for key in exchange_results[timerange]:
            keys.add(key)

        # Add 'names' mapping (sha per report name)
        reports_data[exchange]["names"] = {}
        for trading_mode in reports_info[exchange]:
          for name in reports_info[exchange][trading_mode]:
            reports_data[exchange]["names"][name] = reports_info[exchange][trading_mode][name]["sha"]

        # Build a merged 'timeranges' view — without touching the original 'results'
        reports_data[exchange]["timeranges"] = {}
        for timerange in sorted(timeranges):
          reports_data[exchange]["timeranges"][timerange] = {}
          for key in sorted(keys):
            reports_data[exchange]["timeranges"][timerange][key] = {}
            for trading_mode in reports_info[exchange]:
              for name in sorted(reports_info[exchange][trading_mode]):
                value = reports_data[exchange][trading_mode][name]["results"].get(timerange, {}).get(key, "n/a")
                reports_data[exchange]["timeranges"][timerange][key][name][trading_mode] = value

    pprint.pprint(reports_data)

    try:
      comment_results(options, reports_data)
      parser.exit(0)
    except GithubException as exc:
      parser.exit(1, message=str(exc))


if __name__ == "__main__":
  main()
