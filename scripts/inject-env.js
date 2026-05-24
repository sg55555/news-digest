#!/usr/bin/env node
/**
 * Vercel ビルド時に実行。
 * index.html 内の __SUPABASE_URL__ と __SUPABASE_ANON_KEY__ を
 * Vercel 環境変数で置換する。
 * 未設定の場合は何も変わらず（プレースホルダのまま = ローカル動作モード）。
 */
const fs = require('fs');
const path = require('path');

const htmlPath = path.join(__dirname, '../public/index.html');
let html = fs.readFileSync(htmlPath, 'utf-8');

const url = process.env.SUPABASE_URL || '';
const key = process.env.SUPABASE_ANON_KEY || '';

if (url) html = html.replaceAll('__SUPABASE_URL__', url);
if (key) html = html.replaceAll('__SUPABASE_ANON_KEY__', key);

fs.writeFileSync(htmlPath, html);
console.log(`inject-env: Supabase ${url ? `configured (${url.slice(0,30)}...)` : 'not configured — local mode'}`);
