/** Package the seven SQL export tables for Power BI Service's Excel connector. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sheets = JSON.parse(await fs.readFile(path.join(root, 'data/processed/powerbi_import.json'), 'utf8'));
const workbook = Workbook.create();

function columnLetter(index) {
  let number = index + 1;
  let result = '';
  while (number > 0) {
    number -= 1;
    result = String.fromCharCode(65 + number % 26) + result;
    number = Math.floor(number / 26);
  }
  return result;
}

for (const source of sheets) {
  const sheet = workbook.worksheets.add(source.name);
  const matrix = [source.columns, ...source.rows];
  sheet.getRange(`A1:${columnLetter(source.columns.length - 1)}${matrix.length}`).values = matrix;
  sheet.tables.add(`A1:${columnLetter(source.columns.length - 1)}${matrix.length}`, true, source.name);
  sheet.freezePanes.freezeRows(1);
  sheet.getRange(`A1:${columnLetter(source.columns.length - 1)}1`).format = {
    fill: '#172554', font: { name: 'Arial', bold: true, color: '#FFFFFF', size: 11 },
  };
  sheet.getRange(`A1:${columnLetter(source.columns.length - 1)}1`).format.rowHeight = 25;
  sheet.getRange(`A:${columnLetter(source.columns.length - 1)}`).format.columnWidth = 18;
}

const report = await workbook.inspect({ kind: 'sheet,table', maxChars: 4000, tableMaxRows: 1 });
console.log(report.ndjson ?? report);
const output = await SpreadsheetFile.exportXlsx(workbook);
const file = path.join(root, 'data/processed/semiconductor_powerbi_import.xlsx');
await output.save(file);
console.log(file);
