from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from privateeval.data.manifest import validate_manifest
from privateeval.reporting import render_report
from privateeval.runner import run_experiment
from privateeval.review import import_blinded_ratings, write_review_packet
from privateeval.release_audit import audit_release


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="privateeval")
    subcommands = parser.add_subparsers(dest="command", required=True)
    validate = subcommands.add_parser("validate", help="verify checksums and split boundaries")
    validate.add_argument("--manifest", default="data/manifest.json")
    run = subcommands.add_parser("run", help="run the registered paired evaluation")
    run.add_argument("--config", default="configs/demo.json")
    run.add_argument("--output", default="artifacts/runs/latest")
    report = subcommands.add_parser("report", help="regenerate a Markdown report")
    report.add_argument("--bundle", required=True)
    report.add_argument("--output")
    publish = subcommands.add_parser("sync-demo", help="copy a result bundle into the web demo")
    publish.add_argument("--bundle", required=True)
    publish.add_argument("--output", default="public/results/result_bundle.json")
    review = subcommands.add_parser("review-packet", help="create a fixed blinded review packet and key")
    review.add_argument("--bundle", required=True)
    review.add_argument("--output", default="artifacts/human-review")
    import_ratings = subcommands.add_parser("import-ratings", help="validate and freeze a complete blinded rating export")
    import_ratings.add_argument("--source", required=True)
    import_ratings.add_argument("--packet", default="artifacts/human-review/review_packet.json")
    import_ratings.add_argument("--output", default="data/human_review/ratings.csv")
    audit = subcommands.add_parser("release-audit", help="audit every M5 evidence gate")
    audit.add_argument("--bundle", default="public/results/result_bundle.json")
    audit.add_argument("--output")
    audit.add_argument("--strict", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "validate":
        print(json.dumps(validate_manifest(args.manifest), indent=2))
    elif args.command == "run":
        bundle = run_experiment(args.config, args.output)
        print(json.dumps({"run": bundle["run"], "output": args.output}, indent=2))
    elif args.command == "report":
        bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        report = render_report(bundle)
        if args.output:
            Path(args.output).write_text(report, encoding="utf-8")
        else:
            print(report)
    elif args.command == "sync-demo":
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.bundle, destination)
        print(destination)
    elif args.command == "review-packet":
        bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        paths = write_review_packet(bundle, args.output)
        print(json.dumps({name: str(path) for name, path in paths.items()}, indent=2))
    elif args.command == "import-ratings":
        result = import_blinded_ratings(args.source, args.packet, args.output)
        print(json.dumps(result, indent=2))
    elif args.command == "release-audit":
        result = audit_release(args.bundle)
        rendered = json.dumps(result, indent=2)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        if args.strict and result["status"] != "ready":
            raise SystemExit(1)
