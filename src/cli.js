#!/usr/bin/env node

/**
 * Smaug CLI
 *
 * Commands:
 *   setup    - Interactive setup wizard (recommended for first-time users)
 *   run      - Run the full job (fetch + process with Claude Code)
 *   fetch    - Fetch bookmarks and prepare them for processing
 *   process  - Process pending bookmarks with Claude Code
 *   status   - Show current configuration and status
 *   init     - Create a config file (non-interactive)
 */

import { fetchAndPrepareBookmarks } from './processor.js';
import { refreshVaultIndex, getVaultContext, loadVaultIndex, findObsidianCLI } from './vault-scanner.js';
import { loadPreferences, savePreferences, getPreferenceSummary, addLearnedRule } from './preferences.js';
import { initConfig, loadConfig } from './config.js';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import readline from 'readline';
import { fileURLToPath, pathToFileURL } from 'url';

const args = process.argv.slice(2);
const command = args[0];

function prompt(question) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise(resolve => {
    rl.question(question, answer => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

async function setup() {
  console.log(`
🐉 Smaug Setup Wizard
━━━━━━━━━━━━━━━━━━━━━

This will set up Smaug to automatically archive your Twitter bookmarks.
`);

  // Step 1: Check for bird CLI with bookmarks support (v0.5.0+)
  console.log('Step 1: Checking for bird CLI...');
  try {
    const versionOutput = execSync('bird --version', { stdio: 'pipe', encoding: 'utf8' });
    const versionMatch = versionOutput.match(/(\d+)\.(\d+)\.(\d+)/);

    if (versionMatch) {
      const [, major, minor] = versionMatch.map(Number);
      if (major === 0 && minor < 5) {
        console.log(`  ✗ bird CLI v${versionMatch[0]} found, but v0.5.0+ required for bookmarks support

  Update it:
    npm install -g @steipete/bird@latest

  Or with Homebrew:
    brew upgrade steipete/tap/bird

  Then run this setup again.
`);
        process.exit(1);
      }
      console.log(`  ✓ bird CLI v${versionMatch[0]} found (bookmarks supported)\n`);
    } else {
      console.log('  ✓ bird CLI found\n');
    }
  } catch {
    console.log(`  ✗ bird CLI not found

  Install it:
    npm install -g @steipete/bird@latest

  Or with Homebrew:
    brew install steipete/tap/bird

  Then run this setup again.
`);
    process.exit(1);
  }

  // Step 2: Get Twitter credentials
  console.log(`Step 2: Twitter Authentication

  You need your Twitter cookies to fetch bookmarks.

  To get them:
  1. Open Twitter/X in your browser
  2. Press F12 to open Developer Tools
  3. Go to Application → Cookies → twitter.com
  4. Find 'auth_token' and 'ct0'
`);

  const authToken = await prompt('  Paste your auth_token: ');
  if (!authToken) {
    console.log('  ✗ auth_token is required');
    process.exit(1);
  }

  const ct0 = await prompt('  Paste your ct0: ');
  if (!ct0) {
    console.log('  ✗ ct0 is required');
    process.exit(1);
  }

  // Step 3: Test credentials
  console.log('\nStep 3: Testing credentials...');
  try {
    const env = { ...process.env, AUTH_TOKEN: authToken, CT0: ct0 };
    execSync('bird bookmarks -n 1 --json', { env, stdio: 'pipe', timeout: 30000 });
    console.log('  ✓ Credentials work!\n');
  } catch (error) {
    console.log(`  ✗ Could not fetch bookmarks. Check your credentials and try again.
  Error: ${error.message}
`);
    process.exit(1);
  }

  // Step 4: Create config
  console.log('Step 4: Creating configuration...');
  const config = {
    archiveFile: './bookmarks.md',
    pendingFile: './.state/pending-bookmarks.json',
    stateFile: './.state/bookmarks-state.json',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/New_York',
    twitter: {
      authToken,
      ct0
    },
    autoInvokeClaude: true,
    claudeModel: 'sonnet'
  };

  fs.writeFileSync('./smaug.config.json', JSON.stringify(config, null, 2) + '\n');
  console.log('  ✓ Created smaug.config.json');
  console.log('  ⚠️  This file contains your credentials and is gitignored.');
  console.log('     Never commit it or share it publicly.\n');

  // Step 5: Ask about automation
  console.log('Step 5: Automation Setup\n');
  const wantsCron = await prompt('  Set up automatic fetching every 30 minutes? (y/n): ');

  if (wantsCron.toLowerCase() === 'y') {
    const cwd = process.cwd();
    const cronLine = `*/30 * * * * cd ${cwd} && npx smaug run >> ${cwd}/smaug.log 2>&1`;

    console.log(`
  Add this line to your crontab:

  ${cronLine}

  To edit your crontab, run:
    crontab -e

  Or use PM2 for a simpler setup:
    npm install -g pm2
    pm2 start "npx smaug run" --cron "*/30 * * * *" --name smaug
    pm2 save
`);
  }

  // Step 6: First fetch
  console.log('\nStep 6: Fetching your bookmarks...\n');

  try {
    const result = await fetchAndPrepareBookmarks({ count: 20 });

    if (result.count > 0) {
      console.log(`  ✓ Fetched ${result.count} bookmarks!\n`);
    } else {
      console.log('  ✓ No new bookmarks to fetch (your bookmark list may be empty)\n');
    }
  } catch (error) {
    console.log(`  Warning: Could not fetch bookmarks: ${error.message}\n`);
  }

  // Done!
  console.log(`
━━━━━━━━━━━━━━━━━━━━━
🐉 Setup Complete!
━━━━━━━━━━━━━━━━━━━━━

Your bookmarks will be saved to: ./bookmarks.md

Commands:
  npx smaug run    Run full job (fetch + process with Claude)
  npx smaug fetch  Fetch new bookmarks
  npx smaug status Check status

Happy hoarding! 🐉
`);
}

async function main() {
  switch (command) {
    case 'setup':
      await setup();
      break;

    case 'init':
      initConfig(args[1]);
      break;

    case 'run': {
      // Run the full job (same as node src/job.js)
      const jobPath = path.join(path.dirname(fileURLToPath(import.meta.url)), 'job.js');
      const trackTokens = args.includes('--track-tokens') || args.includes('-t');

      // Parse --limit flag
      const limitIdx = args.findIndex(a => a === '--limit' || a === '-l');
      let limit = null;
      if (limitIdx !== -1 && args[limitIdx + 1]) {
        limit = parseInt(args[limitIdx + 1], 10);
        if (isNaN(limit) || limit <= 0) {
          console.error('Invalid --limit value. Must be a positive number.');
          process.exit(1);
        }
      }

      try {
        const jobModule = await import(pathToFileURL(jobPath).href);
        const result = await jobModule.default.run({ trackTokens, limit });
        process.exit(result.success ? 0 : 1);
      } catch (err) {
        console.error('Failed to run job:', err.message);
        process.exit(1);
      }
      break;
    }

    case 'vault': {
      const vaultArgs = args.slice(1);
      if (vaultArgs.includes('--refresh') || vaultArgs.includes('-r')) {
        console.log('Refreshing vault index via Obsidian CLI...\n');
        try {
          const index = await refreshVaultIndex();
          console.log(`\n✓ Vault indexed: ${index.tags.length} tags found`);
        } catch (err) {
          console.error(`Error: ${err.message}`);
          console.log('\nTo enable Obsidian CLI:');
          console.log('  1. Open Obsidian → Settings → General');
          console.log('  2. Enable "Command line interface"');
          console.log('  3. Restart terminal');
        }
      } else {
        const config = loadConfig();
        const context = getVaultContext(config);
        
        if (!context.cliAvailable) {
          console.log('Obsidian CLI not available.\n');
          console.log('To enable:');
          console.log('  1. Open Obsidian → Settings → General');
          console.log('  2. Enable "Command line interface"');
          console.log('  3. Restart terminal');
          console.log('\nThen run: npx smaug vault --refresh');
        } else {
          console.log('Vault Context (via Obsidian CLI)\n');
          console.log(`Path:         ${context.vaultPath}`);
          console.log(`CLI Status:   ✓ Available at ${context.cliPath}`);
          
          const index = loadVaultIndex(config);
          if (index?.tags?.length > 0) {
            console.log(`\nTags: ${index.tags.slice(0, 30).join(', ')}`);
            if (index.tags.length > 30) {
              console.log(`  ... and ${index.tags.length - 30} more`);
            }
          } else {
            console.log('\nRun: npx smaug vault --refresh to index tags');
          }
        }
      }
      break;
    }

    case 'prefs':
    case 'preferences': {
      const config = loadConfig();
      const prefsArgs = args.slice(1);
      
      if (prefsArgs.includes('--list') || prefsArgs.includes('-l')) {
        const prefs = loadPreferences(config);
        const summary = getPreferenceSummary(prefs);
        console.log('User Preferences\n');
        console.log(`Learned Rules: ${summary.totalRules}`);
        console.log(`Folder Mappings: ${summary.folderMappings}`);
        console.log(`Category Preferences: ${summary.categoryPreferences}`);
        
        if (prefs.learnedRules.length > 0) {
          console.log('\nRecent Rules:');
          prefs.learnedRules.slice(-5).forEach(r => {
            console.log(`  - "${r.condition}" → ${r.action} (used ${r.count}x)`);
          });
        }
      } else if (prefsArgs.includes('--add')) {
        const conditionIdx = prefsArgs.indexOf('--add') + 1;
        const actionIdx = prefsArgs.indexOf('--action') + 1;
        
        if (conditionIdx >= prefsArgs.length || actionIdx >= prefsArgs.length) {
          console.log('Usage: smaug prefs --add "condition" --action "preferred action"');
          console.log('Example: smaug prefs --add "trading" --action "Trading"');
          break;
        }
        
        const condition = prefsArgs[conditionIdx];
        const action = prefsArgs[actionIdx];
        
        const prefs = loadPreferences(config);
        addLearnedRule(prefs, {
          conditionType: 'contains',
          condition,
          action
        });
        savePreferences(prefs, config);
        console.log(`✓ Added rule: "${condition}" → ${action}`);
      } else if (prefsArgs.includes('--clear')) {
        const prefs = loadPreferences(config);
        prefs.learnedRules = [];
        prefs.folderMappings = {};
        prefs.categoryPreferences = {};
        savePreferences(prefs, config);
        console.log('✓ Preferences cleared');
      } else {
        const prefs = loadPreferences(config);
        const summary = getPreferenceSummary(prefs);
        console.log('Preferences\n');
        console.log(`Rules: ${summary.totalRules} learned`);
        console.log(`Mappings: ${summary.folderMappings} folder mappings`);
        console.log('\nCommands:');
        console.log('  smaug prefs --list          Show all preferences');
        console.log('  smaug prefs --add "cond" --action "pref"  Add rule');
        console.log('  smaug prefs --clear         Clear all preferences');
      }
      break;
    }

    case 'account':
    case 'accounts': {
      const config = loadConfig();
      const accountArgs = args.slice(1);
      
      if (accountArgs.includes('--list') || accountArgs.length === 0) {
        const accounts = config.accounts || [];
        console.log('Accounts\n');
        if (accounts.length === 0) {
          console.log('No accounts configured. Using legacy twitter config.');
          if (config.twitter?.authToken) {
            console.log(`  ✓ Legacy account: ${config.twitter.authToken.slice(0, 10)}...`);
          }
        } else {
          accounts.forEach(a => {
            console.log(`  ${a.enabled !== false ? '✓' : '✗'} ${a.name || a.id} (${a.id})`);
          });
        }
      } else if (accountArgs.includes('--add')) {
        const idIdx = accountArgs.indexOf('--add') + 1;
        const nameIdx = accountArgs.indexOf('--name') + 1;
        const authIdx = accountArgs.indexOf('--auth') + 1;
        const ct0Idx = accountArgs.indexOf('--ct0') + 1;
        
        if (idIdx >= accountArgs.length || authIdx >= accountArgs.length || ct0Idx >= accountArgs.length) {
          console.log('Usage: smaug account --add <id> --name "Name" --auth <token> --ct0 <token>');
          console.log('Example: smaug account --add work --name "Work Account" --auth xxx --ct0 yyy');
          break;
        }
        
        const newAccount = {
          id: accountArgs[idIdx],
          name: nameIdx > 0 && nameIdx < accountArgs.length ? accountArgs[nameIdx] : accountArgs[idIdx],
          enabled: true,
          twitter: {
            authToken: accountArgs[authIdx],
            ct0: ct0Idx < accountArgs.length ? accountArgs[ct0Idx] : ''
          }
        };
        
        const accounts = config.accounts || [];
        accounts.push(newAccount);
        config.accounts = accounts;
        
        const fs = await import('fs');
        fs.writeFileSync('./smaug.config.json', JSON.stringify(config, null, 2));
        console.log(`✓ Added account: ${newAccount.name} (${newAccount.id})`);
      } else if (accountArgs.includes('--enable')) {
        const idIdx = accountArgs.indexOf('--enable') + 1;
        if (idIdx >= accountArgs.length) {
          console.log('Usage: smaug account --enable <id>');
          break;
        }
        const targetId = accountArgs[idIdx];
        const accounts = config.accounts || [];
        const acc = accounts.find(a => a.id === targetId);
        if (acc) {
          acc.enabled = true;
          const fs = await import('fs');
          fs.writeFileSync('./smaug.config.json', JSON.stringify(config, null, 2));
          console.log(`✓ Enabled account: ${targetId}`);
        } else {
          console.log(`Account not found: ${targetId}`);
        }
      } else if (accountArgs.includes('--disable')) {
        const idIdx = accountArgs.indexOf('--disable') + 1;
        if (idIdx >= accountArgs.length) {
          console.log('Usage: smaug account --disable <id>');
          break;
        }
        const targetId = accountArgs[idIdx];
        const accounts = config.accounts || [];
        const acc = accounts.find(a => a.id === targetId);
        if (acc) {
          acc.enabled = false;
          const fs = await import('fs');
          fs.writeFileSync('./smaug.config.json', JSON.stringify(config, null, 2));
          console.log(`✓ Disabled account: ${targetId}`);
        } else {
          console.log(`Account not found: ${targetId}`);
        }
      } else {
        console.log('Account Management\n');
        console.log('Commands:');
        console.log('  smaug account                 List accounts');
        console.log('  smaug account --add <id> --auth <token> --ct0 <token> [--name "Name"]');
        console.log('  smaug account --enable <id>   Enable account');
        console.log('  smaug account --disable <id> Disable account');
      }
      break;
    }

    case 'config': {
      const config = loadConfig();
      const configArgs = args.slice(1);
      
      if (configArgs.includes('--llm-model')) {
        const modelIdx = configArgs.indexOf('--llm-model') + 1;
        if (modelIdx >= configArgs.length) {
          console.log('Usage: smaug config --llm-model <model>');
          break;
        }
        const model = configArgs[modelIdx];
        config.llm = config.llm || {};
        config.llm.model = model;
        const fs = await import('fs');
        fs.writeFileSync('./smaug.config.json', JSON.stringify(config, null, 2));
        console.log(`✓ LLM model set to: ${model}`);
      } else if (configArgs.includes('--llm-key')) {
        const keyIdx = configArgs.indexOf('--llm-key') + 1;
        if (keyIdx >= configArgs.length) {
          console.log('Usage: smaug config --llm-key <api-key>');
          break;
        }
        const apiKey = configArgs[keyIdx];
        config.llm = config.llm || {};
        config.llm.apiKey = apiKey;
        const fs = await import('fs');
        fs.writeFileSync('./smaug.config.json', JSON.stringify(config, null, 2));
        console.log('✓ LLM API key updated');
      } else if (configArgs.includes('--schedule')) {
        const intervalIdx = configArgs.indexOf('--schedule') + 1;
        if (intervalIdx >= configArgs.length) {
          console.log('Current schedule:', config.schedule?.enabled ? `${config.schedule.interval || config.schedule.cron}` : 'disabled');
          break;
        }
        const interval = configArgs[intervalIdx];
        config.schedule = config.schedule || {};
        config.schedule.enabled = true;
        // Check if cron or interval
        if (interval.includes('*') || interval.includes('/')) {
          config.schedule.cron = interval;
          config.schedule.interval = null;
        } else {
          config.schedule.interval = interval;
          config.schedule.cron = null;
        }
        const fs = await import('fs');
        fs.writeFileSync('./smaug.config.json', JSON.stringify(config, null, 2));
        console.log(`✓ Schedule set to: ${interval}`);
      } else if (configArgs.includes('--schedule-disable')) {
        config.schedule = config.schedule || {};
        config.schedule.enabled = false;
        const fs = await import('fs');
        fs.writeFileSync('./smaug.config.json', JSON.stringify(config, null, 2));
        console.log('✓ Schedule disabled');
      } else {
        console.log('LLM & Schedule Config\n');
        console.log(`LLM Provider: ${config.llm?.provider || 'openrouter'}`);
        console.log(`LLM Model:   ${config.llm?.model || 'x-ai/grok-4.1-fast'}`);
        console.log(`LLM Key:     ${config.llm?.apiKey ? '***configured***' : 'not set'}`);
        console.log(`Schedule:    ${config.schedule?.enabled ? (config.schedule.cron || config.schedule.interval) : 'disabled'}`);
        console.log('\nCommands:');
        console.log('  smaug config --llm-model <model>     Set LLM model');
        console.log('  smaug config --llm-key <key>         Set LLM API key');
        console.log('  smaug config --schedule <interval>  Set schedule (e.g., 30m, */15 * * * *)');
        console.log('  smaug config --schedule-disable      Disable schedule');
      }
      break;
    }

    case 'fetch': {
      const count = parseInt(args.find(a => a.match(/^\d+$/)) || '20', 10);
      const specificIds = args.filter(a => a.match(/^\d{10,}$/));
      const force = args.includes('--force') || args.includes('-f');
      const includeMedia = args.includes('--media') || args.includes('-m');
      const fetchAll = args.includes('--all') || args.includes('-a') || args.includes('-all');

      // Parse --source flag
      const sourceIdx = args.findIndex(a => a === '--source' || a === '-s');
      let source = null;
      if (sourceIdx !== -1 && args[sourceIdx + 1]) {
        source = args[sourceIdx + 1];
        if (!['bookmarks', 'likes', 'both'].includes(source)) {
          console.error(`Invalid source: ${source}. Must be 'bookmarks', 'likes', or 'both'.`);
          process.exit(1);
        }
      }

      // Parse --max-pages flag
      const maxPagesIdx = args.findIndex(a => a === '--max-pages');
      let maxPages = null;
      if (maxPagesIdx !== -1 && args[maxPagesIdx + 1]) {
        maxPages = parseInt(args[maxPagesIdx + 1], 10);
      }

      const result = await fetchAndPrepareBookmarks({
        count,
        specificIds: specificIds.length > 0 ? specificIds : null,
        force,
        source,
        includeMedia,
        all: fetchAll,
        maxPages
      });

      if (result.count > 0) {
        console.log(`\n✓ Prepared ${result.count} tweets.`);
        console.log(`  Output: ${result.pendingFile}`);
        console.log('\nNext: Run `npx smaug run` to process with Claude');
      } else {
        console.log('\nNo new tweets to process.');
      }
      break;
    }

    case 'process': {
      const config = loadConfig();

      if (!fs.existsSync(config.pendingFile)) {
        console.log('No pending bookmarks. Run `smaug fetch` first.');
        process.exit(0);
      }

      const pending = JSON.parse(fs.readFileSync(config.pendingFile, 'utf8'));

      if (pending.bookmarks.length === 0) {
        console.log('No pending bookmarks to process.');
        process.exit(0);
      }

      console.log(`Found ${pending.bookmarks.length} pending bookmarks.\n`);
      console.log('To process them:');
      console.log('  npx smaug run\n');

      console.log('Pending:');
      for (const b of pending.bookmarks.slice(0, 5)) {
        console.log(`  • @${b.author}: ${b.text.slice(0, 50)}...`);
      }
      if (pending.bookmarks.length > 5) {
        console.log(`  ... and ${pending.bookmarks.length - 5} more`);
      }
      break;
    }

    case 'status': {
      const config = loadConfig();

      console.log('Smaug Status\n');
      console.log(`Archive:     ${config.archiveFile}`);
      console.log(`Source:      ${config.source || 'bookmarks'}`);
      console.log(`Media:       ${config.includeMedia ? '✓ enabled (experimental)' : 'disabled (use --media to enable)'}`);
      console.log(`Twitter:     ${config.twitter?.authToken ? '✓ configured' : '✗ not configured'}`);
      console.log(`Auto-Claude: ${config.autoInvokeClaude ? 'enabled' : 'disabled'}`);

      if (fs.existsSync(config.pendingFile)) {
        const pending = JSON.parse(fs.readFileSync(config.pendingFile, 'utf8'));
        console.log(`Pending:     ${pending.bookmarks.length} bookmarks`);
      } else {
        console.log('Pending:     0 bookmarks');
      }

      if (fs.existsSync(config.stateFile)) {
        const state = JSON.parse(fs.readFileSync(config.stateFile, 'utf8'));
        console.log(`Last fetch:  ${state.last_check || 'never'}`);
      }

      if (fs.existsSync(config.archiveFile)) {
        const content = fs.readFileSync(config.archiveFile, 'utf8');
        const entryCount = (content.match(/^## @/gm) || []).length;
        console.log(`Archived:    ${entryCount} bookmarks`);
      }
      break;
    }

    case 'help':
    case '--help':
    case '-h':
    default:
      console.log(`
🐉 Smaug - Twitter Bookmarks & Likes Archiver

Commands:
  setup          Interactive setup wizard (start here!)
  run            Run the full job (fetch + process with Claude)
  run -t         Run with token usage tracking (--track-tokens)
  run --limit N  Process only N bookmarks (for large backlogs)
  fetch [n]      Fetch n tweets (default: 20)
  fetch --all    Fetch ALL bookmarks (paginated)
  fetch --max-pages N  Limit pagination to N pages (default: 10)
  fetch --force  Re-fetch even if already archived
  fetch --source <source>  Fetch from: bookmarks, likes, or both
  fetch --media  EXPERIMENTAL: Include media attachments
  process        Show pending tweets
  status         Show current status

Examples:
  smaug setup                    # First-time setup
  smaug run                      # Run full automation
  smaug run --limit 50           # Process 50 bookmarks at a time
  smaug fetch                    # Fetch latest (uses config source)
  smaug fetch 50                 # Fetch 50 tweets
  smaug fetch --all              # Fetch ALL bookmarks (paginated)
  smaug fetch --all --max-pages 5  # Fetch up to 5 pages
  smaug fetch --source likes     # Fetch from likes only
  smaug fetch --source both      # Fetch from bookmarks AND likes
  smaug fetch --media            # Include photos/videos/GIFs (experimental)
  smaug fetch --force            # Re-process archived tweets

Config (smaug.config.json):
  "source": "bookmarks"    Default source (bookmarks, likes, or both)
  "includeMedia": false    EXPERIMENTAL: Include media (default: off)
  "folders": {}            Map folder IDs to tags (see README)

More info: https://github.com/lavs9/smaug-obsidian
`);
      break;
  }
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
