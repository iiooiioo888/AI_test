-- Enterprise AI Video Production Platform (AVP)
-- PostgreSQL Database Schema
-- 符合企業級安全標準 (SOC2/ISO27001)

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 全文搜索
CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- 加密

-- ============================================================================
-- 用戶與權限管理 (RBAC)
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url TEXT,
    role VARCHAR(50) DEFAULT 'user',  -- admin, director, editor, viewer
    department VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 審計字段
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active);

-- 角色權限表
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '[]'::jsonb,  -- 權限列表
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    granted_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

-- ============================================================================
-- 項目與劇本管理
-- ============================================================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'active',  -- active, archived, deleted
    visibility VARCHAR(20) DEFAULT 'private',  -- private, team, public
    settings JSONB DEFAULT '{}'::jsonb,  -- 項目配置
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 審計字段
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_name ON projects USING gin(name gin_trgm_ops);

-- 項目成員
CREATE TABLE project_members (
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'viewer',  -- owner, admin, editor, viewer
    permissions JSONB DEFAULT '[]'::jsonb,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id)
);

-- ============================================================================
-- 場景管理 (核心業務表)
-- ============================================================================

CREATE TABLE scenes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    branch VARCHAR(100) DEFAULT 'main',
    
    -- 內容
    title VARCHAR(500) NOT NULL,
    description TEXT,
    narrative_text TEXT NOT NULL,
    
    -- JSON 場景對象 (完整存儲)
    scene_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- 狀態機
    status VARCHAR(50) DEFAULT 'draft',  -- draft, review, locked, queued, generating, completed, failed
    previous_scene_id UUID REFERENCES scenes(id),
    next_scene_id UUID REFERENCES scenes(id),
    
    -- 技術參數
    duration FLOAT DEFAULT 5.0,
    resolution VARCHAR(20) DEFAULT '1920x1080',
    fps INTEGER DEFAULT 24,
    aspect_ratio VARCHAR(10) DEFAULT '16:9',
    
    -- 提示詞
    positive_prompt TEXT NOT NULL,
    negative_prompt TEXT DEFAULT '',
    prompt_weights JSONB DEFAULT '{}'::jsonb,
    style_lora VARCHAR(255),
    character_lora VARCHAR(255),
    
    -- 生成結果
    generated_video_url TEXT,
    generated_thumbnail_url TEXT,
    quality_metrics JSONB DEFAULT '{}'::jsonb,  -- VMAF, CLIP Score 等
    
    -- 協作與審計
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID NOT NULL REFERENCES users(id),
    locked_by UUID REFERENCES users(id),
    locked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 約束
    CONSTRAINT check_version_format CHECK (version ~ '^\d+\.\d+\.\d+$'),
    CONSTRAINT check_duration CHECK (duration > 0 AND duration <= 300)
);

CREATE INDEX idx_scenes_project ON scenes(project_id);
CREATE INDEX idx_scenes_status ON scenes(status);
CREATE INDEX idx_scenes_branch ON scenes(branch);
CREATE INDEX idx_scenes_title ON scenes USING gin(title gin_trgm_ops);
CREATE INDEX idx_scenes_data ON scenes USING gin(scene_data);
CREATE INDEX idx_scenes_created_at ON scenes(created_at DESC);

-- 場景版本歷史
CREATE TABLE scene_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,
    branch VARCHAR(100) DEFAULT 'main',
    scene_data JSONB NOT NULL,
    diff_summary JSONB DEFAULT '[]'::jsonb,  -- 與上一版本的差異
    change_reason TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_scene_version UNIQUE (scene_id, version, branch)
);

CREATE INDEX idx_scene_versions_scene ON scene_versions(scene_id);
CREATE INDEX idx_scene_versions_created_at ON scene_versions(created_at DESC);

-- ============================================================================
-- 角色、道具、地點 (知識圖譜節點)
-- ============================================================================

CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    appearance TEXT NOT NULL,
    personality TEXT,
    relationships JSONB DEFAULT '[]'::jsonb,  -- 與其他角色的關係
    locked_features JSONB DEFAULT '{}'::jsonb,  -- FaceID, LoRA 等鎖定特徵
    reference_images TEXT[] DEFAULT '{}',  -- 參考圖片 URL 數組
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_characters_project ON characters(project_id);
CREATE INDEX idx_characters_name ON characters USING gin(name gin_trgm_ops);

CREATE TABLE props (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,  -- weapon, vehicle, furniture, clothing, other
    importance INTEGER DEFAULT 1 CHECK (importance >= 1 AND importance <= 5),
    reference_images TEXT[] DEFAULT '{}',
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_props_project ON props(project_id);
CREATE INDEX idx_props_type ON props(type);

CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    environment_type VARCHAR(100) NOT NULL,
    lighting VARCHAR(100) DEFAULT 'natural',
    weather VARCHAR(100),
    time_of_day VARCHAR(50) DEFAULT 'noon',
    reference_images TEXT[] DEFAULT '{}',
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_locations_project ON locations(project_id);
CREATE INDEX idx_locations_type ON locations(environment_type);

-- ============================================================================
-- 提示詞管理
-- ============================================================================

CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    negative_prompt TEXT DEFAULT '',
    category VARCHAR(100),  -- style, character, scene, effect
    tags TEXT[] DEFAULT '{}',
    version VARCHAR(20) DEFAULT '1.0.0',
    parent_id UUID REFERENCES prompts(id),  -- 版本繼承
    
    -- 質量指標
    success_rate FLOAT DEFAULT 0,  -- 一次成功率
    reuse_count INTEGER DEFAULT 0,  -- 復用次數
    avg_quality_score FLOAT DEFAULT 0,  -- 平均質量評分
    
    -- 元數據
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_prompt_version CHECK (version ~ '^\d+\.\d+\.\d+$')
);

CREATE INDEX idx_prompts_project ON prompts(project_id);
CREATE INDEX idx_prompts_category ON prompts(category);
CREATE INDEX idx_prompts_tags ON prompts USING gin(tags);
CREATE INDEX idx_prompts_content ON prompts USING gin(content gin_trgm_ops);

-- 提示詞使用歷史
CREATE TABLE prompt_usage_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    scene_id UUID REFERENCES scenes(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id),
    result_quality_score FLOAT,  -- 生成結果質量評分
    user_feedback INTEGER CHECK (user_feedback >= 1 AND user_feedback <= 5),
    feedback_text TEXT,
    tokens_used INTEGER,
    cost_usd FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_prompt_usage_prompt ON prompt_usage_history(prompt_id);
CREATE INDEX idx_prompt_usage_scene ON prompt_usage_history(scene_id);
CREATE INDEX idx_prompt_usage_created_at ON prompt_usage_history(created_at DESC);

-- ============================================================================
-- 視頻生成任務
-- ============================================================================

CREATE TABLE generation_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- 任務狀態
    status VARCHAR(50) DEFAULT 'queued',  -- queued, preparing, generating, processing, completed, failed, cancelled
    progress FLOAT DEFAULT 0,  -- 0-100
    
    -- 模型配置
    model_name VARCHAR(100) NOT NULL,  -- SVD, AnimateDiff, etc.
    model_version VARCHAR(50),
    config JSONB DEFAULT '{}'::jsonb,
    
    -- 資源使用
    gpu_id INTEGER,
    queue_position INTEGER,
    estimated_time_seconds INTEGER,
    actual_time_seconds INTEGER,
    
    -- 結果
    output_url TEXT,
    thumbnail_url TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- 質量評估
    quality_metrics JSONB DEFAULT '{}'::jsonb,  -- VMAF, CLIP Score, etc.
    
    -- 審計
    created_by UUID NOT NULL REFERENCES users(id),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_generation_tasks_scene ON generation_tasks(scene_id);
CREATE INDEX idx_generation_tasks_project ON generation_tasks(project_id);
CREATE INDEX idx_generation_tasks_status ON generation_tasks(status);
CREATE INDEX idx_generation_tasks_created_at ON generation_tasks(created_at DESC);

-- ============================================================================
-- 審計日誌 (合規要求)
-- ============================================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,  -- create, update, delete, login, etc.
    resource_type VARCHAR(50) NOT NULL,  -- user, project, scene, etc.
    resource_id UUID,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- ============================================================================
-- 系統配置
-- ============================================================================

CREATE TABLE system_config (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 插入默認配置
INSERT INTO system_config (key, value, description) VALUES
('video.max_duration', '300', '最大視頻時長 (秒)'),
('video.max_resolution', '3840x2160', '最大解析度'),
('generation.max_concurrent', '10', '最大並發生成任務數'),
('storage.retention_days', '30', '文件保留天數');

-- ============================================================================
-- 觸發器 - 自動更新 updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scenes_updated_at BEFORE UPDATE ON scenes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_characters_updated_at BEFORE UPDATE ON characters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_props_updated_at BEFORE UPDATE ON props
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_locations_updated_at BEFORE UPDATE ON locations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prompts_updated_at BEFORE UPDATE ON prompts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE users IS '用戶賬戶與認證信息';
COMMENT ON TABLE projects IS '視頻製作項目';
COMMENT ON TABLE scenes IS '場景定義與版本管理 (核心業務表)';
COMMENT ON TABLE characters IS '角色定義 (知識圖譜節點)';
COMMENT ON TABLE props IS '道具定義 (知識圖譜節點)';
COMMENT ON TABLE locations IS '地點定義 (知識圖譜節點)';
COMMENT ON TABLE prompts IS '提示詞模板與版本管理';
COMMENT ON TABLE generation_tasks IS '視頻生成任務隊列';
COMMENT ON TABLE audit_logs IS '審計日誌 (SOC2/ISO27001 合規)';
