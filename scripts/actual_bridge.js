#!/usr/bin/env node
/*
 * Minimal bridge to Actual using @actual-app/api.
 * Commands via JSON on stdin, one per line. Responses as JSON per line.
 * Supported commands:
 *   { "cmd": "init", "serverURL": "https://host:port", "password": "...", "dataDir": "..." }
 *   { "cmd": "listBudgets" }
 *   { "cmd": "listAccounts", "budgetId": "...", "budgetPassword": "..." }
 *   { "cmd": "listTransactions", "budgetId": "...", "accountId": "...", "count": 50, "budgetPassword": "..." }
 *   { "cmd": "uploadTransactions", "budgetId": "...", "accountId": "...",
 *     "transactions": [ { date, payee_name, amount, memo } ], "budgetPassword": "..." }
 *
 * Notes:
 * - amount is expected in milliunits from the Python side; we convert to decimal for Actual.
 * - dataDir defaults to ./actual-data under CWD.
 */
const actual = require('@actual-app/api');
const fs = require('fs');
const path = require('path');

function writeResponse(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function getErrorInfo(err) {
  if (!err) {
    return { message: 'Unknown error' };
  }
  if (typeof err === 'string') {
    return { message: err };
  }
  const message = err.message || '';
  const stack = err.stack || '';
  if (message) {
    return { message, stack };
  }
  if (stack) {
    return { message: stack.split('\n')[0], stack };
  }
  return { message: String(err) };
}

async function safeInit(opts) {
  const dataDir = opts.dataDir || path.join(process.cwd(), 'actual-data');
  fs.mkdirSync(dataDir, { recursive: true });
  await actual.init({
    serverURL: opts.serverURL,
    password: opts.password,
    dataDir,
  });
}

async function handleCommand(cmd) {
  try {
    switch (cmd.cmd) {
      case 'init':
        console.error('[Bridge] init', cmd.serverURL);
        await safeInit(cmd);
        return { ok: true };
      case 'listBudgets': {
        console.error('[Bridge] listBudgets');
        const budgets = await actual.getBudgets();
        const mapped = budgets.map(b => ({
          // groupId is the sync id needed by downloadBudget; use it as primary id
          id: b.groupId || b.id || b.cloudFileId || b.fileId || b.syncId || b.uuid,
          name: b.name,
          groupId: b.groupId,
          cloudFileId: b.cloudFileId || b.fileId,
          state: b.state,
        })).filter(b => b.name);
        return { ok: true, budgets: mapped };
      }
      case 'listAccounts': {
        if (!cmd.budgetId) throw new Error('budgetId is required');
        console.error('[Bridge] listAccounts', cmd.budgetId);
        const downloadOpts = cmd.budgetPassword ? { password: cmd.budgetPassword } : undefined;
        await actual.downloadBudget(cmd.budgetId, downloadOpts);
        const accounts = await actual.getAccounts();
        const mapped = accounts.map(a => ({
          id: a.id || a.accountId || a.uuid,
          name: a.name,
        })).filter(a => a.name);
        return { ok: true, accounts: mapped };
      }
      case 'listTransactions': {
        const { budgetId, accountId, count } = cmd;
        if (!budgetId || !accountId) throw new Error('budgetId and accountId are required');
        console.error('[Bridge] listTransactions', budgetId, accountId, count || '');
        const downloadOpts = cmd.budgetPassword ? { password: cmd.budgetPassword } : undefined;
        await actual.downloadBudget(budgetId, downloadOpts);
        let payeeMap = {};
        let accountMap = {};
        try {
          const payees = await actual.getPayees();
          payeeMap = Object.fromEntries((payees || []).map(p => [p.id || p.uuid, p.name]));
        } catch (err) {
          console.error('[Bridge] getPayees failed (continuing without names):', err && err.message ? err.message : err);
        }
        try {
          const accounts = await actual.getAccounts();
          accountMap = Object.fromEntries((accounts || []).map(a => [a.id || a.accountId || a.uuid, a.name]));
        } catch (err) {
          console.error('[Bridge] getAccounts failed (continuing without account map):', err && err.message ? err.message : err);
        }
        const txs = await actual.getTransactions(accountId);
        // Actual amounts are integer cents; convert to milliunits for the UI
        const mapped = (txs || [])
          .map(t => ({
            id: t.id || t.uuid,
            date: t.date,
            // Prefer imported_payee (raw bank description), then explicit payee_name, then lookup id
            payee_name: (() => {
              if (t.imported_payee) return t.imported_payee;
              if (t.payee_name) return t.payee_name;
              const payeeById = payeeMap[t.payee];
              // Avoid showing the account name for transfer payees
              if (payeeById && payeeById !== accountMap[accountId] && payeeById !== accountMap[t.payee]) {
                return payeeById;
              }
              return t.payee || "";
            })(),
            memo: t.notes || t.memo,
            amount: typeof t.amount === 'number' ? Math.trunc(t.amount * 10) : 0,
            import_id: t.imported_id,
          }))
          .sort((a, b) => (a.date || '').localeCompare(b.date || ''));
        const limited = typeof count === 'number' && count > 0 ? mapped.slice(-count) : mapped;
        return { ok: true, transactions: limited };
      }
      case 'uploadTransactions': {
        const { budgetId, accountId, transactions } = cmd;
        if (!budgetId || !accountId) throw new Error('budgetId and accountId are required');
        console.error('[Bridge] uploadTransactions', budgetId, accountId, (transactions || []).length);
        const downloadOpts = cmd.budgetPassword ? { password: cmd.budgetPassword } : undefined;
        await actual.downloadBudget(budgetId, downloadOpts);
        const accounts = await actual.getAccounts();
        const target = (accounts || []).find(a => (a.id || a.accountId || a.uuid) === accountId);
        if (!target) {
          throw new Error(`Account ${accountId} not found in budget; refresh accounts and try again.`);
        }
        // Actual expects integer amount in currency base units (cents); UI sends milliunits
        const formatted = (transactions || []).map(tx => ({
          account: accountId,
          date: tx.date,
          payee_name: tx.payee_name || tx.payee,
          notes: tx.memo || '',
          amount: typeof tx.amount === 'number' ? Math.trunc(tx.amount / 10) : 0,
          cleared: false,
          imported_id: tx.import_id || undefined,
        }));
        // Use addTransactions to avoid Actual's fuzzy dedupe matching by amount within ±7 days.
        await actual.addTransactions(accountId, formatted);
        return { ok: true, uploaded: formatted.length };
      }
      default:
        throw new Error(`Unknown cmd: ${cmd.cmd}`);
    }
  } catch (err) {
    const info = getErrorInfo(err);
    if (info.stack) {
      console.error('[Bridge] error', info.stack);
    } else {
      console.error('[Bridge] error', info.message);
    }
    return { ok: false, error: info.message, details: info.stack || undefined };
  }
}

async function main() {
  // Read JSON lines from stdin
  let buffer = '';
  for await (const chunk of process.stdin) {
    buffer += chunk.toString();
    let idx;
    while ((idx = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (!line) continue;
      let cmd;
      try {
        cmd = JSON.parse(line);
      } catch (e) {
        writeResponse({ ok: false, error: 'Invalid JSON input' });
        continue;
      }
      const resp = await handleCommand(cmd);
      writeResponse(resp);
    }
  }
}

main().catch(err => {
  writeResponse({ ok: false, error: err && err.message ? err.message : String(err) });
  process.exit(1);
});
