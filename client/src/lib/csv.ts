/**
 * "Export CSV" for any chart: the exact rows the chart shows, in the units the user sees.
 * Missing values are empty cells (not 0). Values that could be read as formulas by Excel
 * ("=", "+", "-", "@" at the start of TEXT) are prefixed with ' (CSV injection).
 */
export interface CsvColumn<Row> {
  header: string;
  value: (row: Row) => string | number | null | undefined;
}

function cell(value: string | number | null | undefined): string {
  if (value === null || value === undefined || (typeof value === "number" && Number.isNaN(value))) return "";
  if (typeof value === "number") return String(Math.round(value * 100) / 100);
  const text = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function toCsv<Row>(rows: Row[], columns: CsvColumn<Row>[]): string {
  const lines = [columns.map((c) => cell(c.header)).join(",")];
  for (const row of rows) lines.push(columns.map((c) => cell(c.value(row))).join(","));
  return `${lines.join("\r\n")}\r\n`;
}

export function safeFilename(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "export";
}

export function downloadCsv(filename: string, csv: string): void {
  // BOM so Excel opens UTF-8 (°, é) correctly
  const blob = new Blob(["﻿", csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
