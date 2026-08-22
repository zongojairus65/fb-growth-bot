CREATE TABLE profiles (
    id SERIAL PRIMARY KEY,
    fb_username TEXT NOT NULL,
    fb_page_id TEXT,
    niche TEXT,
    audience TEXT,
    objectif TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE quiz_answers (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id),
    question_id TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE diagnostics (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id),
    niche_detectee TEXT,
    resume TEXT,
    hashtags JSONB,
    points_forts JSONB,
    points_faibles JSONB,
    raw_stats JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE content_ideas (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id),
    concept TEXT,
    hook TEXT,
    format TEXT,
    angle_psychologique TEXT,
    justification_engagement TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE post_drafts (
    id SERIAL PRIMARY KEY,
    idea_id INTEGER REFERENCES content_ideas(id),
    format TEXT,
    contenu TEXT,
    legende TEXT,
    cta TEXT,
    status TEXT DEFAULT 'brouillon',
    fb_post_id TEXT,
    posted_at TIMESTAMP
);

CREATE TABLE posts_history (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id),
    fb_post_id TEXT,
    message TEXT,
    format TEXT,
    impressions INTEGER,
    engagement_rate FLOAT,
    posted_at TIMESTAMP
);
