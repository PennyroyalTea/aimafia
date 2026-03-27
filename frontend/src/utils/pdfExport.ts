import type { GameAnalysis, PersonalAdvice } from "../types";

function esc(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function adviceCardHtml(a: PersonalAdvice): string {
  const role = a.role
    ? ` <span style="color:#666;font-weight:400">(${esc(a.role)})</span>`
    : "";
  let h = `<div style="font-weight:700;font-size:11px;margin-bottom:4px">${esc(a.player_name)}${role}</div>`;

  if (a.good_plays.length) {
    h += `<div style="font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#2e7d32;margin:6px 0 2px">Good plays</div>`;
    h += `<ul style="padding-left:14px;margin:0">${a.good_plays.map((p) => `<li style="margin-bottom:2px;font-size:9px">${esc(p)}</li>`).join("")}</ul>`;
  }

  if (a.mistakes.length) {
    h += `<div style="font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#c62828;margin:6px 0 2px">Mistakes</div>`;
    h += `<ul style="padding-left:14px;margin:0">${a.mistakes.map((m) => `<li style="margin-bottom:2px;font-size:9px">${esc(m)}</li>`).join("")}</ul>`;
  }

  h += `<div style="font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#4a50c8;margin:6px 0 2px">Coaching</div>`;
  h += `<div style="font-size:9px;line-height:1.4">${esc(a.advice)}</div>`;

  return h;
}

function buildPdfHtml(game: GameAnalysis): string {
  const { summary, advice } = game;

  const winnerMap: Record<string, { bg: string; color: string; text: string }> =
    {
      mafia: { bg: "#fce4e4", color: "#c62828", text: "Mafia wins" },
      citizens: { bg: "#e8f5e9", color: "#2e7d32", text: "Citizens win" },
      unknown: { bg: "#f5f5f5", color: "#616161", text: "Unknown outcome" },
    };
  const w = winnerMap[summary.winner] || winnerMap.unknown;

  let html = "";

  // ---- Page 1: Summary ----
  if (summary.title) {
    html += `<h1 style="font-size:18px;margin:0 0 8px;font-weight:700">${esc(summary.title)}</h1>`;
  }

  html += `<span style="display:inline-block;padding:4px 12px;border-radius:4px;font-weight:600;font-size:13px;background:${w.bg};color:${w.color}">${w.text}</span>`;
  html += `<p style="font-size:11px;margin:12px 0;white-space:pre-line;line-height:1.6">${esc(summary.summary)}</p>`;

  if (summary.key_moments.length) {
    html += `<h3 style="font-size:13px;margin:14px 0 6px;border-bottom:1px solid #e0e0e0;padding-bottom:3px">Key moments</h3>`;
    html += `<ul style="padding-left:18px;margin:0 0 8px">${summary.key_moments.map((m) => `<li style="font-size:10px;margin-bottom:3px">${esc(m)}</li>`).join("")}</ul>`;
  }

  if (summary.players.length) {
    html += `<h3 style="font-size:13px;margin:14px 0 6px;border-bottom:1px solid #e0e0e0;padding-bottom:3px">Players</h3>`;
    html += `<table style="width:100%;border-collapse:collapse">`;
    for (let i = 0; i < summary.players.length; i += 2) {
      const left = summary.players[i];
      const right = summary.players[i + 1];
      html += `<tr>`;
      html += `<td style="padding:4px 8px 4px 0;border-bottom:1px solid #eee;vertical-align:top;width:50%;font-size:10px"><strong>${esc(left.player_name)}</strong>${left.role ? ` <span style="color:#666">(${esc(left.role)})</span>` : ""}<br/><span style="color:#444">${esc(left.summary)}</span></td>`;
      if (right) {
        html += `<td style="padding:4px 0 4px 8px;border-bottom:1px solid #eee;vertical-align:top;width:50%;font-size:10px"><strong>${esc(right.player_name)}</strong>${right.role ? ` <span style="color:#666">(${esc(right.role)})</span>` : ""}<br/><span style="color:#444">${esc(right.summary)}</span></td>`;
      } else {
        html += `<td></td>`;
      }
      html += `</tr>`;
    }
    html += `</table>`;
  }

  // Page break
  html += `<div style="page-break-after:always"></div>`;

  // ---- Page 2+: Advice ----
  html += `<h2 style="font-size:16px;margin:0 0 10px;font-weight:700">Personal coaching</h2>`;
  html += `<table style="width:100%;border-collapse:separate;border-spacing:5px">`;
  for (let i = 0; i < advice.length; i += 2) {
    const left = advice[i];
    const right = advice[i + 1];
    html += `<tr>`;
    html += `<td style="width:50%;vertical-align:top;border:1px solid #ddd;border-radius:6px;padding:8px">${adviceCardHtml(left)}</td>`;
    if (right) {
      html += `<td style="width:50%;vertical-align:top;border:1px solid #ddd;border-radius:6px;padding:8px">${adviceCardHtml(right)}</td>`;
    } else {
      html += `<td></td>`;
    }
    html += `</tr>`;
  }
  html += `</table>`;

  return html;
}

export async function exportPdf(
  game: GameAnalysis,
  filename = "game-analysis.pdf"
): Promise<void> {
  const html2pdf = (await import("html2pdf.js")).default;

  const container = document.createElement("div");
  container.style.cssText = `
    position: fixed; top: 0; left: 0; width: 794px;
    background: white; color: #1a1a1a; padding: 40px;
    font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
    line-height: 1.5; z-index: -1;
  `;
  container.innerHTML = buildPdfHtml(game);
  document.body.appendChild(container);

  try {
    await html2pdf()
      .set({
        margin: 0,
        filename,
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, logging: false },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
        pagebreak: { mode: ["css"] },
      } as Record<string, unknown>)
      .from(container)
      .save();
  } finally {
    document.body.removeChild(container);
  }
}
