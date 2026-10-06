"""Generate every paper number and plot from the saved full-run result."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def pdf_plot(path: Path, points: list[tuple[float, float]], reference: float, labels: list[tuple[float, float, str]]) -> None:
    """Write a small vector PDF using only the PDF core graphics operators."""
    commands = ["0.6 w 0 0 0 RG 50 40 m 50 230 l S 50 40 m 540 40 l S",
                f"0.6 0.6 0.6 RG 50 {reference:.3f} m 540 {reference:.3f} l S", "0.12 0.36 0.65 RG 1.4 w"]
    commands.append(" ".join(f"{x:.3f} {y:.3f} {'m' if i == 0 else 'l'}" for i, (x, y) in enumerate(points)) + " S")
    for x, y, label in labels:
        safe = label.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"BT /F1 10 Tf {x:.3f} {y:.3f} Td ({safe}) Tj ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 580 260] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"]
    payload = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(payload))
        payload.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(payload)
    payload.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode())
    payload.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(payload)


def analyse(results: Path, root: Path) -> None:
    result = json.loads(results.read_text())
    if result["mode"] != "full":
        raise ValueError("Paper analysis requires full results, not a smoke run")
    metrics = result["metrics"]
    for key in ("estimate_pi", "reference_pi", "absolute_error", "standard_error"):
        if not math.isfinite(metrics[key]):
            raise ValueError(f"Non-finite metric: {key}")
    generated, figures = root / "paper/generated", root / "paper/figures"
    generated.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    macros = {"SampleCount": str(metrics["n"]), "SeedValue": str(metrics["seed"]), "PiEstimate": f"{metrics['estimate_pi']:.6f}", "PiReference": f"{metrics['reference_pi']:.6f}", "AbsoluteError": f"{metrics['absolute_error']:.6f}", "StandardError": f"{metrics['standard_error']:.6f}"}
    (generated / "metrics.tex").write_text("% Generated from results; do not edit.\n" + "\n".join(f"\\newcommand{{\\{key}}}{{{value}}}" for key, value in macros.items()) + "\n")
    (generated / "table.tex").write_text(r"""\begin{tabular}{lr}
\hline
Metric & Value \\
\hline
Sample count & \SampleCount \\
Pi estimate & \PiEstimate \\
Analytical reference & \PiReference \\
Absolute error & \AbsoluteError \\
Monte Carlo standard error & \StandardError \\
\hline
\end{tabular}
""")
    checkpoints = metrics["checkpoints"]
    values = [x["estimate_pi"] for x in checkpoints] + [metrics["reference_pi"]]
    low, high = min(values) - 0.005, max(values) + 0.005
    xmap = lambda n: 50 + 490 * n / metrics["n"]
    ymap = lambda value: 40 + 190 * (value - low) / (high - low)
    points = [(xmap(row["n"]), ymap(row["estimate_pi"])) for row in checkpoints]
    labels = [(50, 12, "0"), (490, 12, str(metrics["n"])), (215, 12, "Sample count"), (7, 43, f"{low:.3f}"), (7, 225, f"{high:.3f}"), (50, 244, "Monte Carlo pi estimate; grey line: analytical reference")]
    pdf_plot(figures / "convergence.pdf", points, ymap(metrics["reference_pi"]), labels)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="580" height="260" viewBox="0 0 580 260">', '<rect width="580" height="260" fill="white"/>', '<path d="M50 30 V220 H540" fill="none" stroke="black"/>', f'<path d="M50 {260-ymap(metrics["reference_pi"]):.3f} H540" stroke="#999"/>', '<polyline fill="none" stroke="#1f5ca6" stroke-width="1.4" points="' + ' '.join(f'{x:.3f},{260-y:.3f}' for x, y in points) + '"/>']
    svg.extend(f'<text x="{x}" y="{260-y}" font-family="sans-serif" font-size="10">{label}</text>' for x, y, label in labels)
    svg.append('</svg>')
    (figures / "convergence.svg").write_text("\n".join(svg) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    analyse(args.results, Path(__file__).resolve().parents[1])
