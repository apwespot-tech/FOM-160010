// Приём заявок с сайта в Google Таблицу.
// Вставляется в редактор: Таблица → Расширения → Apps Script (см. ИНСТРУКЦИЯ-ФОРМА.md)

const SHEET_NAME = "Заявки";
const HEADERS = ["Дата", "Имя", "Кто", "Контакт", "Уровень", "Комментарий", "Страница"];

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.tryLock(10000);
  try {
    const p = (e && e.parameter) || {};
    // ловушка для ботов: настоящий человек это поле не видит и не заполняет
    if (p.website) return reply_({ ok: true });

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
      sheet.setFrozenRows(1);
    }

    sheet.appendRow([
      new Date(),
      clean_(p.name),
      clean_(p.role),
      clean_(p.contact),
      clean_(p.level),
      clean_(p.comment),
      clean_(p.page),
    ]);
    return reply_({ ok: true });
  } catch (err) {
    return reply_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

// Обрезаем длину и не даём тексту стать формулой (=, +, -, @ в начале)
function clean_(value) {
  const s = String(value || "").trim().slice(0, 1000);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function reply_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
