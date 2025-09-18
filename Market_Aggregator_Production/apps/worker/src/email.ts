import { escapeHtml, isUsMarketClosedNY } from "./util";
import type { Env } from "./util";
import type { MarketQuote } from "./market-data";

export interface EmailItem {
  title: string;
  url: string;
  source: string;
  published_at: string | null;
}

export async function sendDigestEmail(
  env: Env,
  to: string[],
  subject: string,
  summaryHtml: string,
  marketData: MarketQuote[],
  items: EmailItem[],
  fromAddress?: string,
  stats?: { feeds_ok: number; feeds_total: number; articles_seen: number; articles_used: number; ai_provider?: string }
): Promise<{ ok: boolean; error?: string }>{
  if (!env.RESEND_API_KEY) return { ok: false, error: "missing RESEND_API_KEY" };
  const html = renderHtml(subject, summaryHtml, marketData, items, stats);
  const text = renderText(subject, summaryHtml, marketData, items);
  try {
    const resp = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: fromAddress || (env as any).RESEND_FROM || "Market Intel <digest@yourdomain.com>",
        to,
        subject,
        html,
        text,
      }),
    });
    if (!resp.ok) {
      const text = await resp.text();
      return { ok: false, error: `resend status ${resp.status}: ${text.slice(0, 500)}` };
    }
    return { ok: true };
  } catch (e: any) {
    return { ok: false, error: String(e) };
  }
}

function renderHtml(
  subject: string,
  summaryHtml: string,
  marketData: MarketQuote[],
  items: EmailItem[],
  stats?: { feeds_ok: number; feeds_total: number; articles_seen: number; articles_used: number; ai_provider?: string }
): string {
  const marketTable = generateMarketTable(marketData);
  const styledSummary = applyStoryCards(styleSummaryHtml(summaryHtml));
  return `<!doctype html>
<html><head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>${escapeHtml(subject)}</title>
</head>
<body style="margin:0;padding:0;background:#f6f7f9;">
  <div style="width:100%;background:#f6f7f9;padding:16px 0;">
    <div style="max-width:720px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
      <div style="padding:16px 16px 0 16px;">
        <h1 style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:22px;line-height:1.3;color:#111;margin:0 0 6px;">📊 Daily Market & News Intelligence</h1>
        <p style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#666;font-size:12px;margin:0 0 6px;">Generated: ${new Date().toISOString().replace('T',' ').replace('Z',' UTC')}</p>
        ${renderMarketBadge()}
        ${stats ? `<div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:13px;color:#444;margin:4px 0 12px;">
          <div><strong>Analysis by:</strong> ${escapeHtml(stats.ai_provider || 'Gemini')}</div>
          <div><strong>Data Sources:</strong> ${stats.articles_used ?? items.length} articles from ${stats.feeds_ok ?? '?'} / ${stats.feeds_total ?? '?'} feeds</div>
        </div>` : ''}
        <h2 style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:18px;margin:12px 0 8px;color:#111;">SECTION 1 - MARKET PERFORMANCE</h2>
        ${marketTable}
      </div>
      <div style="padding:0 16px 16px 16px;">
        ${styledSummary}
        <hr style="margin:24px 0;border:none;border-top:1px solid #eee"/>
        <p style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#666;font-size:12px;margin:0;">
          🤖 AI Market Intelligence System<br/>
          Tracking: ${escapeHtml(marketData.map(m => m.symbol).join(' | ') || items.map(i => i.source).join(' | '))}
        </p>
      </div>
    </div>
  </div>
</body></html>`;
}

function generateMarketTable(marketData: MarketQuote[]): string {
  if (!marketData || marketData.length === 0) return `<p style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#666;font-size:14px;margin:8px 0 16px;">No market data available.</p>`;
  const headerCell = "padding:8px;border:1px solid #e5e7eb;background:#f9fafb;text-align:left;font-size:13px;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;";
  const cell = "padding:8px;border:1px solid #e5e7eb;text-align:left;font-size:14px;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;";
  const rows = marketData.map((m) => {
    const green = "color:#16a34a;";
    const red = "color:#dc2626;";
    const change = `${m.change >= 0 ? "+" : ""}${m.change.toFixed(2)}`;
    const pct = `${m.changePercent >= 0 ? "+" : ""}${m.changePercent.toFixed(2)}%`;
    const color = m.change >= 0 ? green : red;
    return `<tr>
      <td style="${cell}">${escapeHtml(m.symbol)}</td>
      <td style="${cell}">${m.price.toFixed(2)}</td>
      <td style="${cell}${color}">${change}</td>
      <td style="${cell}${color}">${pct}</td>
    </tr>`;
  }).join("");
  return `<table cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse;width:100%;margin:8px 0 16px;">
    <thead><tr>
      <th style="${headerCell}">Symbol</th>
      <th style="${headerCell}">Price</th>
      <th style="${headerCell}">Change</th>
      <th style="${headerCell}">% </th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function styleSummaryHtml(html: string): string {
  // Inline simple styles for headings, paragraphs, and lists to survive email clients.
  let s = html;
  // Replace placeholder dates with actual date (New York)
  const nyDateStr = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'long', month: 'long', day: '2-digit', year: 'numeric' }).format(new Date());
  s = s.replace(/\[(?:Current\s+Date|Today|current\s+date)\]/gi, nyDateStr);
  s = s.replace(/<h2>/g, '<h2 style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:18px;margin:18px 0 8px;color:#111;">');
  s = s.replace(/<h3>/g, '<h3 style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:16px;margin:14px 0 6px;color:#111;">');
  s = s.replace(/<p>/g, '<p style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:15px;line-height:1.55;color:#111;margin:8px 0;">');
  s = s.replace(/<ul>/g, '<ul style="margin:8px 0 8px 20px;padding:0;">');
  s = s.replace(/<li>/g, '<li style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:15px;line-height:1.55;color:#111;margin:4px 0;">');
  s = s.replace(/<a /g, '<a style="color:#0b79d0;text-decoration:none;" ');
  return s;
}

function renderMarketBadge(): string {
  const nyWeekday = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'long' }).format(new Date());
  const nyDate = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', month: 'short', day: '2-digit' }).format(new Date());
  const closed = isUsMarketClosedNY(new Date());
  const style = 'display:inline-block;padding:4px 8px;border-radius:999px;font-size:12px;margin:6px 0;background:' + (closed ? '#fee2e2' : '#dcfce7') + ';color:' + (closed ? '#991b1b' : '#065f46') + ';border:1px solid ' + (closed ? '#fecaca' : '#bbf7d0') + ';font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;';
  const label = closed ? 'Market Closed' : 'Market Day';
  return `<div style="${style}">🗓️ ${nyWeekday}, ${nyDate} • ${label}</div>`;
}

function applyStoryCards(html: string): string {
  // Wrap each "Story Title" block and its following paragraphs until the next Story Title or section heading
  try {
    const pattern = /(\s*<p><strong>Story Title<\/strong>:[\s\S]*?<\/p>)([\s\S]*?)(?=(\s*<p><strong>Story Title<\/strong>:)|\s*<h2|\s*<h3|$)/g;
    return html.replace(pattern, (_m, head: string, body: string) => {
      const cardStyle = 'border:1px solid #e5e7eb;border-radius:8px;padding:12px;margin:10px 0;background:#ffffff;box-shadow:0 1px 2px rgba(0,0,0,0.04);';
      const bodyStyled = body
        .replace(/<p>/g, '<p style="margin:8px 0;">')
        .replace(/<ul>/g, '<ul style="margin:8px 0 8px 18px;">')
        .replace(/<li>/g, '<li style="margin:4px 0;">');
      return `<div style="${cardStyle}">${head}${bodyStyled}</div>`;
    });
  } catch {
    return html;
  }
}

function renderText(
  subject: string,
  summaryHtml: string,
  marketData: MarketQuote[],
  items: EmailItem[]
): string {
  const lines: string[] = [];
  lines.push(`Daily Market & News Intelligence`);
  lines.push(`Subject: ${subject}`);
  lines.push("");
  lines.push("SECTION 1 - MARKET PERFORMANCE");
  for (const m of marketData) {
    const change = `${m.change >= 0 ? "+" : ""}${m.change.toFixed(2)}`;
    const pct = `${m.changePercent >= 0 ? "+" : ""}${m.changePercent.toFixed(2)}%`;
    lines.push(`- ${m.symbol}: ${m.price.toFixed(2)} (${change}, ${pct})`);
  }
  lines.push("");
  // Strip tags from summaryHtml for a text fallback
  const stripped = summaryHtml.replace(/<[^>]+>/g, '').replace(/\s+\n/g, '\n');
  lines.push(stripped);
  lines.push("");
  lines.push("Top Sources:");
  for (const it of items.slice(0, 10)) {
    lines.push(`- ${it.title} (${it.source}) ${it.url}`);
  }
  return lines.join("\n");
}
