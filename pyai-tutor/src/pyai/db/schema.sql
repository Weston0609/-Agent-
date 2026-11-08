-- pyai-tutor 数据库 schema（权威源）。用 stdlib sqlite3 执行，零 ORM 依赖。
-- 课程树层级：semester → unit → lesson → kp（原始 YAML 无 chapters 层，已合并）。

-- 用户
CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    name       TEXT,
    level      TEXT DEFAULT 'beginner',
    timezone   TEXT DEFAULT 'Asia/Shanghai',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 周课表槽位（参考学校模式：固定的每周上课时间）
CREATE TABLE IF NOT EXISTS schedule_slots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT REFERENCES users(id),
    weekday         INTEGER,          -- 0-6 (周一=0)
    start_minute    INTEGER,          -- 从当天 00:00 起算的分钟
    duration_minutes INTEGER,
    enabled         BOOLEAN DEFAULT 1
);

-- 课程树
CREATE TABLE IF NOT EXISTS semesters (
    id     TEXT PRIMARY KEY,
    name   TEXT,
    "order" INTEGER
);
CREATE TABLE IF NOT EXISTS units (
    id          TEXT PRIMARY KEY,
    semester_id TEXT,
    name        TEXT,
    "order"     INTEGER
);
CREATE TABLE IF NOT EXISTS lessons (
    id     TEXT PRIMARY KEY,
    unit_id TEXT,
    name   TEXT,
    "order" INTEGER
);
CREATE TABLE IF NOT EXISTS kps (
    id         TEXT PRIMARY KEY,
    lesson_id  TEXT REFERENCES lessons(id),
    title      TEXT,
    difficulty INTEGER DEFAULT 1,
    prereq     TEXT DEFAULT '[]',     -- JSON ["py.type.list"]
    weight     INTEGER DEFAULT 3,     -- 对 AI 架构师的重要度 1-5
    "order"    INTEGER
);

-- 知识点内容（预生成，日常直接读）
CREATE TABLE IF NOT EXISTS kp_content (
    kp_id        TEXT PRIMARY KEY REFERENCES kps(id),
    explain      TEXT,
    example_code TEXT,
    pitfalls     TEXT,
    sources      TEXT DEFAULT '[]',   -- JSON [{url, hash, fetched_at}]
    version      INTEGER DEFAULT 1,
    generated_at TIMESTAMP,
    verified     BOOLEAN DEFAULT 0,
    source       TEXT DEFAULT 'generated'  -- generated（管道生成）/ seed（手写种子，不覆盖 generated）
);

-- 题库（预生成）
CREATE TABLE IF NOT EXISTS questions (
    id            TEXT PRIMARY KEY,
    kp_id         TEXT REFERENCES kps(id),
    type          TEXT,               -- single_choice / multi_choice / fill_blank / code_reading / scenario
    difficulty    INTEGER DEFAULT 1,
    stem          TEXT,
    options       TEXT DEFAULT '[]',
    answer        TEXT,               -- JSON
    explanation   TEXT,
    error_tag     TEXT,               -- 概念混淆 / 记忆缺失 / ...
    source_ref    TEXT,
    variant_group TEXT,
    required_keywords TEXT DEFAULT '[]',  -- JSON：场景题判分靠它命中率
    source        TEXT DEFAULT 'generated'  -- generated / seed（种子题 id 为 <kp_id>-seed<i>）
);

-- 学习状态（BKT 掌握度）
CREATE TABLE IF NOT EXISTS mastery (
    user_id   TEXT,
    kp_id     TEXT,
    p_mastery REAL DEFAULT 0.2,
    attempts  INTEGER DEFAULT 0,
    correct   INTEGER DEFAULT 0,
    last_seen TIMESTAMP,
    PRIMARY KEY (user_id, kp_id)
);

-- 复习队列（FSRS）
CREATE TABLE IF NOT EXISTS review_queue (
    user_id     TEXT,
    kp_id       TEXT,
    due_at      TIMESTAMP,
    stability   REAL,
    difficulty  REAL,
    reps        INTEGER,
    lapses      INTEGER,
    last_review TIMESTAMP,
    card_json   TEXT,                 -- fsrs Card.to_dict() 全量 JSON，供无损重建
    PRIMARY KEY (user_id, kp_id)
);

-- 每课测验结果（闯关门禁：测验 ≥ pass_threshold 即通过该课）
CREATE TABLE IF NOT EXISTS lesson_progress (
    user_id    TEXT,
    lesson_id  TEXT,
    quiz_score REAL DEFAULT 0,
    attempts   INTEGER DEFAULT 0,
    passed     INTEGER DEFAULT 0,
    updated_at TIMESTAMP,
    PRIMARY KEY (user_id, lesson_id)
);

-- 当前卷子（打 Boss 的题面）
-- 组卷必须「取题与判分看到同一批题」，否则学生答对自己看到的题，却被按另一批题判分。
-- 旧实现按 attempts 现算卷子，而 attempts 每次提交都 +1 → 重做必然错位。改为落库固定。
CREATE TABLE IF NOT EXISTS quiz_papers (
    user_id      TEXT,
    lesson_id    TEXT,
    question_ids TEXT NOT NULL,     -- JSON 数组，有序；判分按同一顺序
    created_at   TIMESTAMP,
    PRIMARY KEY (user_id, lesson_id)
);

-- 打 Boss 的消费账：记录用过的题，保证重做优先换没做过的。
-- 题池用完才允许重复（按使用次数从少到多挑）。换卷时清掉本课旧记录 = 允许循环复用。
CREATE TABLE IF NOT EXISTS quiz_history (
    user_id     TEXT,
    lesson_id   TEXT,
    question_id TEXT,
    used_at     TIMESTAMP,
    PRIMARY KEY (user_id, lesson_id, question_id)
);

-- 错题日志
CREATE TABLE IF NOT EXISTS error_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT,
    kp_id       TEXT,
    question_id TEXT,
    user_answer TEXT,
    error_type  TEXT,
    at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 补强队列（课堂未完成项，供明日 warmup / 补强）
CREATE TABLE IF NOT EXISTS warmup_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT,
    kp_id      TEXT,
    note       TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 学习会话
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    user_id     TEXT,
    lesson_id   TEXT,
    plan_date   DATE,
    stage       TEXT,
    state_json  TEXT,
    started_at  TIMESTAMP,
    ended_at    TIMESTAMP,
    tokens_used INTEGER DEFAULT 0
);

-- 每日排课
CREATE TABLE IF NOT EXISTS day_plans (
    user_id      TEXT,
    plan_date    DATE,
    lessons      TEXT,                -- JSON 排课结果
    generated_at TIMESTAMP,
    PRIMARY KEY (user_id, plan_date)
);

-- 系统更新日志
CREATE TABLE IF NOT EXISTS updates_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT,                 -- weekly / manual
    started_at  TIMESTAMP,
    ended_at    TIMESTAMP,
    tokens_used INTEGER,
    kps_added   INTEGER,
    kps_updated INTEGER,
    status      TEXT
);

-- 审计结果
CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary    TEXT
);

-- 通知收件箱（上课提醒 / 缺席召回 / 更新完成；离线可读）
CREATE TABLE IF NOT EXISTS notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT NOT NULL,
    kind       TEXT NOT NULL,          -- class / recall / update / info
    message    TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id, read_at);

-- 章节考 / 学期考成绩（学校式层级门禁）
--   scope='unit'     → 章节考，覆盖该单元全部课的题目，通过线 70%
--   scope='semester' → 学期考，覆盖该学期全部单元的题目，通过线 75%
-- 每课自己的小测仍记在 lesson_progress（单元考线 75%）。
CREATE TABLE IF NOT EXISTS exam_results (
    user_id    TEXT,
    scope      TEXT,               -- unit / semester
    scope_id   TEXT,               -- s1u1 / s1
    score      REAL DEFAULT 0,
    attempts   INTEGER DEFAULT 0,
    passed     INTEGER DEFAULT 0,
    updated_at TIMESTAMP,
    PRIMARY KEY (user_id, scope, scope_id)
);
