#!/usr/bin/env node
/**
 * 审计 skills/ 下每个技能目录是否符合本仓库的发布门禁与写作规范。
 * 用法：node scripts/audit-skills.mjs [skillsDir]
 * 机器可读 JSON 输出到 stdout，人读摘要输出到 stderr；有 error 时退出码 1。
 */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { parse } from 'yaml';

const root = process.argv[2] ?? 'skills';
// 与 AGENTS.md「Best Practices for Context Efficiency」一致：SKILL.md 应 < 500 行
const MAX_LINES = 500;
const MAX_NAME = 64;
const MAX_DESCRIPTION = 1024;
const NAME_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
// 正文里出现的相对资源引用，用于发现「文档提到了但文件不存在」的断链
// 后缀交替必须「长优先 + 词边界」：否则 \.jsonc 会先命中 js 分支被截成 .js，产生假断链。
const REFERENCE_PATTERN =
  /((?:references|scripts|templates|docs|examples|lib)\/[\w\-./\[\]]+\.(?:jsonc|jsonl|ndjson|drawio|json|yaml|yml|toml|mjs|py|sh|js|md|xml|txt|csv|ini))(?!\w)/g;
// 行内声明「该路径是运行时产物/示例，不要求随技能存在」：audit-ignore: <path>
const IGNORE_PATTERN = /audit-ignore:\s*([\w\-./\[\]]+)/g;

const findings = [];
const report = (level, skill, message) => findings.push({ level, skill, message });

const directories = readdirSync(root)
  .filter((entry) => statSync(join(root, entry)).isDirectory())
  .sort();

const seen = new Map();
const summary = [];

const walk = (directory, base = '') => {
  const entries = readdirSync(directory, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const relative = base ? `${base}/${entry.name}` : entry.name;
    return entry.isDirectory()
      ? walk(join(directory, entry.name), relative)
      : [relative];
  });
};

for (const directory of directories) {
  const skillDirectory = join(root, directory);
  const skillFile = join(skillDirectory, 'SKILL.md');

  if (!existsSync(skillFile)) {
    report(
      'error',
      directory,
      '缺少 SKILL.md — build-discovery-index.mjs 会在 git show 阶段抛错，导致整个发布会失败',
    );
    continue;
  }

  const source = readFileSync(skillFile, 'utf8');
  const lineCount = source.split(/\r?\n/).length;
  const files = walk(skillDirectory);

  // ---- frontmatter ----
  const frontmatterMatch = source.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!frontmatterMatch) {
    report('error', directory, '缺少 YAML frontmatter（必须以 --- 开头）');
    continue;
  }

  let metadata;
  try {
    metadata = parse(frontmatterMatch[1]);
  } catch (error) {
    report('error', directory, `frontmatter 无法解析：${error.message}`);
    continue;
  }

  const { name, description, ...extraKeys } = metadata ?? {};

  // ---- name ----
  if (typeof name !== 'string' || name.length === 0) {
    report('error', directory, 'frontmatter 缺少 name');
  } else {
    if (!NAME_PATTERN.test(name)) {
      report('error', directory, `name 不匹配 ^[a-z0-9]+(?:-[a-z0-9]+)*$：${name}`);
    }
    if (name.length > MAX_NAME) {
      report('error', directory, `name 超过 ${MAX_NAME} 字符：${name.length}`);
    }
    if (name !== directory) {
      report(
        'warn',
        directory,
        `name (${name}) 与目录名不一致 — 产物按 name 命名，目录名仅影响人工定位`,
      );
    }
    if (seen.has(name)) {
      report('error', directory, `name 与 ${seen.get(name)} 重复 — 构建脚本要求 name 全局唯一`);
    } else {
      seen.set(name, directory);
    }
  }

  // ---- description ----
  if (typeof description !== 'string' || description.length === 0) {
    report('error', directory, 'frontmatter 缺少 description');
  } else if (description.length > MAX_DESCRIPTION) {
    report(
      'error',
      directory,
      `description 超过 ${MAX_DESCRIPTION} 字符：${description.length}`,
    );
  } else if (description.length < 40) {
    report('warn', directory, `description 过短（${description.length} 字符），难以精确触发`);
  }

  // ---- 非标准 frontmatter 字段 ----
  const unexpected = Object.keys(extraKeys).filter(
    (key) => !['license', 'allowed-tools', 'version', 'metadata'].includes(key),
  );
  if (unexpected.length > 0) {
    report(
      'warn',
      directory,
      `frontmatter 含非标准字段（构建时被丢弃）：${unexpected.join(', ')}`,
    );
  }
  if (extraKeys['disable-model-invocation'] === true) {
    report(
      'warn',
      directory,
      'disable-model-invocation: true 与 discovery index 的「可被发现」语义冲突 — 发布后宿主可能仍自动加载',
    );
  }

  // ---- 篇幅（progressive disclosure）----
  if (lineCount > MAX_LINES) {
    report(
      'warn',
      directory,
      `SKILL.md ${lineCount} 行，超过 ${MAX_LINES} 行建议值 — 应把细节拆到 references/`,
    );
  }

  // ---- 断链检查 ----
  const ignored = new Set(
    [...source.matchAll(IGNORE_PATTERN)].map((match) => match[1]),
  );
  const missing = new Set();
  for (const match of source.matchAll(REFERENCE_PATTERN)) {
    const target = match[1];
    if (ignored.has(target)) continue;
    if (!existsSync(join(skillDirectory, target))) missing.add(target);
  }
  if (missing.size > 0) {
    report(
      'warn',
      directory,
      `SKILL.md 引用了不存在的路径：${[...missing].slice(0, 5).join(', ')}${
        missing.size > 5 ? ` 等 ${missing.size} 处` : ''
      }`,
    );
  }

  // ---- 产物形态 ----
  const artifactType =
    files.length === 1 ? 'skill-md' : 'archive (tar.gz)';
  if (files.length === 1) {
    report(
      'info',
      directory,
      '仅含 SKILL.md — 发布为单文件 .md 产物，无法携带辅助文件',
    );
  }

  summary.push({
    name: name ?? directory,
    directory,
    lines: lineCount,
    files: files.length,
    descriptionLength: typeof description === 'string' ? description.length : 0,
    artifactType,
  });
}

// ---- 技能清单双向比对（README §技能清单 是唯一事实源）----
// REV-00 的教训：校验锚点一旦不存在就整段静默跳过，门禁会假通过。
// 因此「清单段缺失」本身必须报 error，而不是当成「没有可校验内容」。
{
  const readmePath = join(root, '..', 'README.md');
  if (!existsSync(readmePath)) {
    report('error', 'README.md', '仓库根缺少 README.md — 技能清单无事实源');
  } else {
    const readme = readFileSync(readmePath, 'utf8');
    const sectionMatch = readme.match(/^##\s*技能清单\s*$([\s\S]*?)(?=^##\s)/m);
    if (!sectionMatch) {
      report(
        'error',
        'README.md',
        '缺少「## 技能清单」段 — 清单与磁盘的双向比对无从执行，门禁失效',
      );
    } else {
      const listed = new Map();
      for (const match of sectionMatch[1].matchAll(/^\|\s*`([a-z0-9-]+)`\s*\|/gm)) {
        listed.set(match[1], (listed.get(match[1]) ?? 0) + 1);
      }
      if (listed.size === 0) {
        report('error', 'README.md', '「## 技能清单」段内没有解析到任何 `name` 条目');
      }
      for (const [name, times] of listed) {
        if (times > 1) {
          report('error', 'README.md', `清单里 ${name} 重复登记 ${times} 次`);
        }
        if (!seen.has(name)) {
          report('error', 'README.md', `清单登记了 ${name}，但 skills/ 下无此技能（孤儿条目）`);
        }
      }
      for (const name of seen.keys()) {
        if (!listed.has(name)) {
          report('error', 'README.md', `skills/${name} 未登记在「## 技能清单」中`);
        }
      }
    }
  }
}

const order = { error: 0, warn: 1, info: 2 };
findings.sort(
  (a, b) => order[a.level] - order[b.level] || a.skill.localeCompare(b.skill),
);
summary.sort((a, b) => b.lines - a.lines);

for (const item of findings) {
  if (item.level !== 'info') {
    process.stderr.write(`${item.level.toUpperCase().padEnd(5)} ${item.skill}: ${item.message}\n`);
  }
}
const count = (level) => findings.filter((item) => item.level === level).length;
process.stderr.write(
  `\n审计 ${summary.length} 个技能：${count('error')} error, ${count('warn')} warn, ${count('info')} info\n`,
);

process.stdout.write(
  `${JSON.stringify({ root, skills: summary, findings }, null, 2)}\n`,
);

process.exit(count('error') > 0 ? 1 : 0);
