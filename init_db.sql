-- Create database (run this first if database doesn't exist)
-- CREATE DATABASE code_review;

-- Connect to code_review database and run the following:

-- Create reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    review_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    repository VARCHAR(500),
    file_path VARCHAR(1000),
    language VARCHAR(50) NOT NULL,
    code_hash VARCHAR(64) NOT NULL,
    summary TEXT,
    findings JSONB,
    refactoring_suggestions JSONB,
    test_recommendations JSONB,
    model_results JSONB,
    consensus_score FLOAT,
    processing_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_code_hash ON reviews(code_hash);

-- Verify
SELECT 'Database initialized successfully!' AS status;
