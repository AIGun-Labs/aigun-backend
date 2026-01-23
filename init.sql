-- =====================================================
-- AI Gun Backend Database Initialization Script
-- =====================================================

-- Create schema if not exists (using public as default)
CREATE SCHEMA IF NOT EXISTS public;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- TABLE DEFINITIONS
-- =====================================================

-- 1. User Table
CREATE TABLE IF NOT EXISTS "user" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    tid BIGINT UNIQUE,
    email VARCHAR(255),
    nickname VARCHAR(255),
    avatar VARCHAR(500),
    invite_code VARCHAR(50),
    superior_id VARCHAR(255),
    ancestor_id VARCHAR(255),
    invite_amount INTEGER DEFAULT 0,
    indirect_invite_amount INTEGER DEFAULT 0,
    expand_invite_list VARCHAR(255) DEFAULT '0|0|0',
    power BIGINT DEFAULT 0 NOT NULL,
    claimed_amount BIGINT DEFAULT 0,
    destroyed_amount BIGINT DEFAULT 0,
    reward_claimed_amount BIGINT DEFAULT 0,
    reward_destroyed_amount BIGINT DEFAULT 0,
    reward_unclaimed_amount BIGINT DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    is_obsolete INTEGER DEFAULT 0,
    role_id INTEGER DEFAULT 1,
    device_id VARCHAR(255) DEFAULT '',
    wallet_user_id VARCHAR(255),
    organization_id VARCHAR(255),
    total_trading_volume VARCHAR(50) DEFAULT '0' NOT NULL,
    aigun_claimed_amount VARCHAR(50) DEFAULT '0' NOT NULL,
    unclaimed_invite_gold VARCHAR(50) DEFAULT '0' NOT NULL,
    unclaimed_trade_gold VARCHAR(50) DEFAULT '0' NOT NULL,
    claimed_dollar NUMERIC(38, 18) DEFAULT 0 NOT NULL
);

-- 2. Chain Table
CREATE TABLE IF NOT EXISTS chain (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    is_active BOOLEAN DEFAULT TRUE,
    slug TEXT UNIQUE,
    network_id TEXT,
    type TEXT,
    main_token TEXT,
    name TEXT,
    symbol TEXT,
    rpcs JSONB,
    logo TEXT,
    okx_chain_index TEXT
);

-- 3. Entity Table
CREATE TABLE IF NOT EXISTS entity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    name VARCHAR(255),
    type VARCHAR(100),
    influence_level TEXT,
    influence_score DOUBLE PRECISION,
    locations JSONB,
    description TEXT,
    source TEXT,
    avatar VARCHAR(500),
    extra_data JSONB,
    is_test BOOLEAN NOT NULL DEFAULT FALSE,
    is_visible BOOLEAN DEFAULT TRUE NOT NULL,
    subtype TEXT
);

-- 4. Tag Table
CREATE TABLE IF NOT EXISTS tag (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    slug VARCHAR(255),
    is_visible BOOLEAN DEFAULT TRUE NOT NULL
);

-- 5. Subset Table
CREATE TABLE IF NOT EXISTS subset (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tags JSONB DEFAULT '[]',
    type VARCHAR(50) NOT NULL
);

-- 6. Account Table
CREATE TABLE IF NOT EXISTS account (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    twitter_id BIGINT NOT NULL,
    screen_name TEXT NOT NULL,
    name TEXT NOT NULL,
    avatar TEXT NOT NULL,
    banner TEXT,
    description TEXT,
    desc_urls JSONB,
    categories JSONB,
    display_urls JSONB,
    aff_highlight_labels JSONB,
    joined_at BIGINT NOT NULL,
    verified_status TEXT DEFAULT 'unverified' NOT NULL,
    follower_count BIGINT,
    following_count BIGINT,
    location TEXT,
    source JSONB,
    level INTEGER DEFAULT 0 NOT NULL,
    "group" INTEGER DEFAULT 0 NOT NULL,
    is_monitoring BOOLEAN DEFAULT FALSE NOT NULL,
    tags JSONB,
    version INTEGER DEFAULT 1 NOT NULL,
    entry_source TEXT,
    type TEXT
);

-- 7. Intelligence Table
CREATE TABLE IF NOT EXISTS intelligence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP(3),
    updated_at TIMESTAMP WITH TIME ZONE,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_visible BOOLEAN DEFAULT TRUE NOT NULL,
    is_valuable BOOLEAN,
    source_id UUID,
    source_url TEXT,
    type TEXT,
    subtype TEXT,
    title TEXT,
    content TEXT,
    abstract TEXT,
    extra_datas JSONB,
    medias JSONB,
    analyzed JSONB,
    score DOUBLE PRECISION,
    tags JSONB,
    analyzed_time BIGINT DEFAULT 0,
    showed_tokens JSONB,
    spider_time TIMESTAMP WITH TIME ZONE,
    push_time TIMESTAMP WITH TIME ZONE,
    adjusted_tokens JSONB
);

-- 8. Project Table (TokenModel)
CREATE TABLE IF NOT EXISTS project (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    entity_id UUID,
    name TEXT,
    symbol TEXT,
    description TEXT,
    logo TEXT,
    established_at TIMESTAMP,
    issued_at TIMESTAMP,
    lending_total DOUBLE PRECISION
);

-- 9. Token Table (TokenChainDataModel)
CREATE TABLE IF NOT EXISTS token (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    is_visible BOOLEAN DEFAULT TRUE,
    entity_id UUID,
    project_id UUID,
    chain_id UUID,
    contract_address TEXT,
    decimals INTEGER,
    name TEXT,
    symbol TEXT,
    logo TEXT,
    type TEXT,
    lifi_coin_key TEXT,
    volume_24h FLOAT DEFAULT 0,
    market_cap FLOAT DEFAULT 0,
    price_usd FLOAT DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    description TEXT,
    price_change_24h FLOAT DEFAULT 0,
    standard TEXT,
    network TEXT,
    version TEXT,
    liquidity FLOAT DEFAULT 0,
    display_time TIMESTAMP,
    is_native BOOLEAN DEFAULT FALSE,
    is_internal BOOLEAN DEFAULT FALSE,
    is_mainstream BOOLEAN DEFAULT FALSE,
    is_follow BOOLEAN DEFAULT FALSE
);

-- 10. Entity Datasource Table
CREATE TABLE IF NOT EXISTS entity_datasource (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    entity_id UUID,
    account_id UUID,
    account_type TEXT,
    is_visible BOOLEAN DEFAULT TRUE NOT NULL,
    account_slug TEXT,
    url TEXT,
    extra_data JSONB
);

-- 11. Entity Tag Table
CREATE TABLE IF NOT EXISTS entity_tag (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    entity_id UUID,
    tag_id UUID,
    type VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS idx_entity_tag_entity_id ON entity_tag(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_tag_tag_id ON entity_tag(tag_id);

-- 12. Entity Intelligence Table
CREATE TABLE IF NOT EXISTS entity_intelligence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    entity_id UUID NOT NULL,
    intelligence_id UUID NOT NULL,
    type TEXT,
    master_type TEXT,
    master_id UUID,
    highest_increase_rate FLOAT DEFAULT 0,
    warning_price_usd FLOAT DEFAULT 0,
    warning_market_cap FLOAT DEFAULT 0
);

-- 13. Tag Intelligence Table
CREATE TABLE IF NOT EXISTS tag_intelligence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    tag_id UUID NOT NULL,
    intelligence_id UUID NOT NULL,
    type TEXT
);

-- 14. User Subset Table
CREATE TABLE IF NOT EXISTS user_subset (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    user_id UUID NOT NULL,
    subset_id UUID NOT NULL
);

-- 15. AI Agent Table
CREATE TABLE IF NOT EXISTS ai_agent (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    name JSONB NOT NULL,
    description JSONB,
    avatar TEXT,
    rank INTEGER NOT NULL,
    subset_id UUID,
    tag_id UUID
);

-- 16. News Platform Table
CREATE TABLE IF NOT EXISTS news_platform (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    name TEXT,
    content_type TEXT,
    extra_data JSONB,
    entity_id UUID,
    type TEXT,
    interval TEXT
);

-- 17. Exchange Platform Table
CREATE TABLE IF NOT EXISTS exchange_platform (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    entity_id UUID,
    type TEXT,
    name TEXT,
    content_type TEXT,
    interval TEXT,
    extra_data JSONB
);

-- 18. Token Social Links Table
CREATE TABLE IF NOT EXISTS token_social_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    network TEXT,
    contract_address TEXT,
    link_type TEXT,
    url TEXT,
    rank INTEGER
);

-- =====================================================
-- SAMPLE DATA
-- =====================================================

-- Define fixed UUIDs for referential integrity
-- Users
INSERT INTO "user" (id, tid, email, nickname, avatar, invite_code, power, is_active, role_id, wallet_user_id, organization_id) VALUES
('11111111-1111-1111-1111-111111111101', 1001, 'alice@example.com', 'Alice', 'https://avatar.example.com/alice.png', 'ALICE001', 1000, 1, 1, 'wallet_alice', 'org_001'),
('11111111-1111-1111-1111-111111111102', 1002, 'bob@example.com', 'Bob', 'https://avatar.example.com/bob.png', 'BOB002', 2500, 1, 1, 'wallet_bob', 'org_001'),
('11111111-1111-1111-1111-111111111103', 1003, 'charlie@example.com', 'Charlie', 'https://avatar.example.com/charlie.png', 'CHARLIE003', 500, 1, 1, 'wallet_charlie', 'org_002'),
('11111111-1111-1111-1111-111111111104', 1004, 'diana@example.com', 'Diana', 'https://avatar.example.com/diana.png', 'DIANA004', 3200, 1, 2, 'wallet_diana', 'org_002'),
('11111111-1111-1111-1111-111111111105', 1005, 'eve@example.com', 'Eve', 'https://avatar.example.com/eve.png', 'EVE005', 1800, 1, 1, 'wallet_eve', 'org_003'),
('11111111-1111-1111-1111-111111111106', 1006, 'frank@example.com', 'Frank', 'https://avatar.example.com/frank.png', 'FRANK006', 4100, 1, 1, 'wallet_frank', 'org_003'),
('11111111-1111-1111-1111-111111111107', 1007, 'grace@example.com', 'Grace', 'https://avatar.example.com/grace.png', 'GRACE007', 900, 1, 1, 'wallet_grace', 'org_004'),
('11111111-1111-1111-1111-111111111108', 1008, 'henry@example.com', 'Henry', 'https://avatar.example.com/henry.png', 'HENRY008', 5500, 1, 3, 'wallet_henry', 'org_004'),
('11111111-1111-1111-1111-111111111109', 1009, 'ivy@example.com', 'Ivy', 'https://avatar.example.com/ivy.png', 'IVY009', 2100, 1, 1, 'wallet_ivy', 'org_005'),
('11111111-1111-1111-1111-111111111110', 1010, 'jack@example.com', 'Jack', 'https://avatar.example.com/jack.png', 'JACK010', 3800, 1, 1, 'wallet_jack', 'org_005');

-- Chains
INSERT INTO chain (id, slug, network_id, type, main_token, name, symbol, rpcs, logo, okx_chain_index, is_active) VALUES
('22222222-2222-2222-2222-222222222201', 'ethereum', '1', 'evm', 'ETH', 'Ethereum', 'ETH', '["https://mainnet.infura.io/v3/", "https://eth.llamarpc.com"]', 'https://chain.example.com/eth.png', '1', true),
('22222222-2222-2222-2222-222222222202', 'bsc', '56', 'evm', 'BNB', 'BNB Smart Chain', 'BSC', '["https://bsc-dataseed1.binance.org/"]', 'https://chain.example.com/bsc.png', '56', true),
('22222222-2222-2222-2222-222222222203', 'polygon', '137', 'evm', 'MATIC', 'Polygon', 'MATIC', '["https://polygon-rpc.com/"]', 'https://chain.example.com/polygon.png', '137', true),
('22222222-2222-2222-2222-222222222204', 'arbitrum', '42161', 'evm', 'ETH', 'Arbitrum One', 'ARB', '["https://arb1.arbitrum.io/rpc"]', 'https://chain.example.com/arb.png', '42161', true),
('22222222-2222-2222-2222-222222222205', 'optimism', '10', 'evm', 'ETH', 'Optimism', 'OP', '["https://mainnet.optimism.io"]', 'https://chain.example.com/op.png', '10', true),
('22222222-2222-2222-2222-222222222206', 'avalanche', '43114', 'evm', 'AVAX', 'Avalanche', 'AVAX', '["https://api.avax.network/ext/bc/C/rpc"]', 'https://chain.example.com/avax.png', '43114', true),
('22222222-2222-2222-2222-222222222207', 'solana', 'solana', 'solana', 'SOL', 'Solana', 'SOL', '["https://api.mainnet-beta.solana.com"]', 'https://chain.example.com/sol.png', 'solana', true),
('22222222-2222-2222-2222-222222222208', 'base', '8453', 'evm', 'ETH', 'Base', 'BASE', '["https://mainnet.base.org"]', 'https://chain.example.com/base.png', '8453', true),
('22222222-2222-2222-2222-222222222209', 'fantom', '250', 'evm', 'FTM', 'Fantom', 'FTM', '["https://rpc.ftm.tools/"]', 'https://chain.example.com/ftm.png', '250', true),
('22222222-2222-2222-2222-222222222210', 'sui', 'sui', 'move', 'SUI', 'Sui', 'SUI', '["https://fullnode.mainnet.sui.io"]', 'https://chain.example.com/sui.png', 'sui', true);

-- Entities
INSERT INTO entity (id, name, type, influence_level, influence_score, description, source, avatar, is_test, is_visible, subtype) VALUES
('33333333-3333-3333-3333-333333333301', 'Vitalik Buterin', 'kol', 'high', 95.5, 'Ethereum co-founder', 'twitter', 'https://avatar.example.com/vitalik.png', false, true, 'developer'),
('33333333-3333-3333-3333-333333333302', 'CZ Binance', 'kol', 'high', 92.0, 'Former Binance CEO', 'twitter', 'https://avatar.example.com/cz.png', false, true, 'exchange'),
('33333333-3333-3333-3333-333333333303', 'Binance', 'exchange', 'high', 98.0, 'Largest crypto exchange by volume', 'official', 'https://avatar.example.com/binance.png', false, true, 'cex'),
('33333333-3333-3333-3333-333333333304', 'Coinbase', 'exchange', 'high', 95.0, 'US-based crypto exchange', 'official', 'https://avatar.example.com/coinbase.png', false, true, 'cex'),
('33333333-3333-3333-3333-333333333305', 'Uniswap', 'protocol', 'high', 90.0, 'Leading DEX protocol', 'official', 'https://avatar.example.com/uniswap.png', false, true, 'dex'),
('33333333-3333-3333-3333-333333333306', 'Elon Musk', 'kol', 'high', 88.0, 'Tesla CEO, crypto influencer', 'twitter', 'https://avatar.example.com/elon.png', false, true, 'celebrity'),
('33333333-3333-3333-3333-333333333307', 'Michael Saylor', 'kol', 'high', 85.0, 'MicroStrategy chairman', 'twitter', 'https://avatar.example.com/saylor.png', false, true, 'institutional'),
('33333333-3333-3333-3333-333333333308', 'OpenSea', 'protocol', 'medium', 75.0, 'NFT marketplace', 'official', 'https://avatar.example.com/opensea.png', false, true, 'nft'),
('33333333-3333-3333-3333-333333333309', 'Aave', 'protocol', 'high', 88.0, 'DeFi lending protocol', 'official', 'https://avatar.example.com/aave.png', false, true, 'defi'),
('33333333-3333-3333-3333-333333333310', 'Circle', 'agency', 'high', 82.0, 'USDC issuer', 'official', 'https://avatar.example.com/circle.png', false, true, 'stablecoin');

-- Tags
INSERT INTO tag (id, slug, is_visible) VALUES
('44444444-4444-4444-4444-444444444401', 'defi', true),
('44444444-4444-4444-4444-444444444402', 'nft', true),
('44444444-4444-4444-4444-444444444403', 'layer2', true),
('44444444-4444-4444-4444-444444444404', 'bitcoin', true),
('44444444-4444-4444-4444-444444444405', 'ethereum', true),
('44444444-4444-4444-4444-444444444406', 'solana', true),
('44444444-4444-4444-4444-444444444407', 'meme', true),
('44444444-4444-4444-4444-444444444408', 'gamefi', true),
('44444444-4444-4444-4444-444444444409', 'exchange', true),
('44444444-4444-4444-4444-444444444410', 'regulation', true);

-- Subsets
INSERT INTO subset (id, name, description, tags, type) VALUES
('55555555-5555-5555-5555-555555555501', 'DeFi Signals', 'DeFi protocol updates and signals', '["defi", "lending", "dex"]', 'ai_agent'),
('55555555-5555-5555-5555-555555555502', 'NFT Alerts', 'NFT market movements and drops', '["nft", "art", "collectibles"]', 'ai_agent'),
('55555555-5555-5555-5555-555555555503', 'Layer 2 News', 'L2 scaling solutions updates', '["layer2", "rollup", "scaling"]', 'ai_agent'),
('55555555-5555-5555-5555-555555555504', 'KOL Tracker', 'Track key opinion leaders', '["kol", "influencer"]', 'social_network'),
('55555555-5555-5555-5555-555555555505', 'Exchange Updates', 'Centralized exchange news', '["exchange", "cex", "listing"]', 'ai_agent'),
('55555555-5555-5555-5555-555555555506', 'Bitcoin News', 'Bitcoin related updates', '["bitcoin", "btc"]', 'ai_agent'),
('55555555-5555-5555-5555-555555555507', 'Ethereum Updates', 'Ethereum ecosystem news', '["ethereum", "eth", "evm"]', 'ai_agent'),
('55555555-5555-5555-5555-555555555508', 'Meme Coins', 'Meme coin alerts and signals', '["meme", "doge", "shib"]', 'ai_agent'),
('55555555-5555-5555-5555-555555555509', 'GameFi Signals', 'Gaming and metaverse updates', '["gamefi", "gaming", "metaverse"]', 'ai_agent'),
('55555555-5555-5555-5555-555555555510', 'Regulation Watch', 'Regulatory news and policy', '["regulation", "policy", "legal"]', 'ai_agent');

-- Accounts (Twitter)
INSERT INTO account (id, twitter_id, screen_name, name, avatar, banner, description, joined_at, verified_status, follower_count, following_count, location, level, "group", is_monitoring, version, type) VALUES
('66666666-6666-6666-6666-666666666601', 295218901, 'VitalikButerin', 'vitalik.eth', 'https://pbs.twimg.com/profile_images/vitalik.jpg', 'https://pbs.twimg.com/profile_banners/vitalik.jpg', 'Ethereum', 1309961606000, 'verified', 5200000, 380, 'Earth', 3, 1, true, 1, 'kol'),
('66666666-6666-6666-6666-666666666602', 902926941413453824, 'caborc', 'CZ Binance', 'https://pbs.twimg.com/profile_images/cz.jpg', 'https://pbs.twimg.com/profile_banners/cz.jpg', 'Just a guy who builds', 1504188706000, 'verified', 8800000, 420, 'Global', 3, 1, true, 1, 'kol'),
('66666666-6666-6666-6666-666666666603', 44196397, 'elonmusk', 'Elon Musk', 'https://pbs.twimg.com/profile_images/elon.jpg', 'https://pbs.twimg.com/profile_banners/elon.jpg', 'Mars awaits', 1243981480000, 'verified', 170000000, 650, 'Mars', 3, 1, true, 1, 'kol'),
('66666666-6666-6666-6666-666666666604', 361289499, 'saborc', 'Michael Saylor', 'https://pbs.twimg.com/profile_images/saylor.jpg', 'https://pbs.twimg.com/profile_banners/saylor.jpg', 'Bitcoin is hope', 1314049878000, 'verified', 3200000, 210, 'Miami', 3, 1, true, 1, 'kol'),
('66666666-6666-6666-6666-666666666605', 877807935493033984, 'Uniswap', 'Uniswap Labs', 'https://pbs.twimg.com/profile_images/uniswap.jpg', '', 'Swap anything', 1498176000000, 'verified', 1100000, 85, 'NYC', 2, 2, true, 1, 'protocol'),
('66666666-6666-6666-6666-666666666606', 357312062, 'binance', 'Binance', 'https://pbs.twimg.com/profile_images/binance.jpg', 'https://pbs.twimg.com/profile_banners/binance.jpg', 'Build the future', 1313625600000, 'verified', 11500000, 120, 'Global', 3, 2, true, 1, 'exchange'),
('66666666-6666-6666-6666-666666666607', 574032254, 'coinbase', 'Coinbase', 'https://pbs.twimg.com/profile_images/coinbase.jpg', '', 'Update the system', 1336608000000, 'verified', 5800000, 150, 'San Francisco', 3, 2, true, 1, 'exchange'),
('66666666-6666-6666-6666-666666666608', 913153344679976961, 'opensea', 'OpenSea', 'https://pbs.twimg.com/profile_images/opensea.jpg', '', 'NFT marketplace', 1506672000000, 'verified', 2400000, 95, 'NYC', 2, 2, true, 1, 'protocol'),
('66666666-6666-6666-6666-666666666609', 958065937448198144, 'AaveAave', 'Aave', 'https://pbs.twimg.com/profile_images/aave.jpg', '', 'Open source liquidity', 1517356800000, 'verified', 650000, 78, 'London', 2, 2, true, 1, 'protocol'),
('66666666-6666-6666-6666-666666666610', 2407102374, 'circle', 'Circle', 'https://pbs.twimg.com/profile_images/circle.jpg', '', 'USDC issuer', 1395360000000, 'verified', 480000, 110, 'Boston', 2, 2, true, 1, 'agency');

-- Intelligences
INSERT INTO intelligence (id, published_at, is_visible, is_valuable, type, subtype, title, content, abstract, score, tags, analyzed_time) VALUES
('77777777-7777-7777-7777-777777777701', '2024-01-15 10:30:00+00', true, true, 'twitter', 'kol_post', 'Ethereum upgrade announcement', 'Excited to share that the next Ethereum upgrade is on track for Q2. Major improvements to gas efficiency incoming!', 'ETH upgrade Q2 with gas improvements', 0.85, '["ethereum", "upgrade", "defi"]', 1705315800000),
('77777777-7777-7777-7777-777777777702', '2024-01-16 14:20:00+00', true, true, 'twitter', 'kol_post', 'Binance new listing', 'New token listing coming tomorrow. Stay tuned! #Binance', 'Binance announces new listing', 0.72, '["binance", "listing", "exchange"]', 1705415800000),
('77777777-7777-7777-7777-777777777703', '2024-01-17 09:00:00+00', true, true, 'news', 'regulation', 'SEC crypto enforcement action', 'SEC announces new enforcement actions against unregistered crypto offerings', 'SEC enforcement on unregistered offerings', -0.65, '["regulation", "sec", "legal"]', 1705485600000),
('77777777-7777-7777-7777-777777777704', '2024-01-18 16:45:00+00', true, true, 'twitter', 'kol_post', 'Bitcoin ETF approval impact', 'The ETF approval is just the beginning. Institutional adoption will accelerate from here.', 'Bitcoin ETF driving institutional adoption', 0.92, '["bitcoin", "etf", "institutional"]', 1705599900000),
('77777777-7777-7777-7777-777777777705', '2024-01-19 11:15:00+00', true, false, 'twitter', 'protocol_update', 'Uniswap V4 development update', 'Uniswap V4 hooks are revolutionary. Builders can now customize every aspect of liquidity.', 'Uniswap V4 hooks enable customization', 0.78, '["uniswap", "defi", "dex"]', 1705665300000),
('77777777-7777-7777-7777-777777777706', '2024-01-20 08:30:00+00', true, true, 'news', 'market', 'Bitcoin hits new ATH', 'Bitcoin surpasses previous all-time high amid strong institutional buying', 'BTC new ATH on institutional demand', 0.95, '["bitcoin", "ath", "bullish"]', 1705741800000),
('77777777-7777-7777-7777-777777777707', '2024-01-21 13:00:00+00', true, true, 'telegram', 'alpha', 'New Solana memecoin launching', 'Insider info: Major memecoin launch on Solana this week. Early birds advantage.', 'Solana memecoin launch alert', 0.45, '["solana", "meme", "launch"]', 1705842000000),
('77777777-7777-7777-7777-777777777708', '2024-01-22 17:30:00+00', true, true, 'twitter', 'kol_post', 'Layer 2 TVL milestone', 'Layer 2 solutions now hold over $20B in TVL. Scaling is working!', 'L2 TVL exceeds $20B milestone', 0.82, '["layer2", "scaling", "tvl"]', 1705944600000),
('77777777-7777-7777-7777-777777777709', '2024-01-23 10:00:00+00', true, false, 'news', 'partnership', 'Major bank enters crypto', 'Goldman Sachs announces crypto custody services for institutional clients', 'Goldman Sachs launches crypto custody', 0.88, '["institutional", "custody", "banking"]', 1706004000000),
('77777777-7777-7777-7777-777777777710', '2024-01-24 15:45:00+00', true, true, 'twitter', 'security', 'DeFi hack alert', 'Breaking: Protocol X exploited for $50M. Funds being traced. Users advised to revoke approvals.', 'DeFi protocol hacked for $50M', -0.90, '["hack", "security", "defi"]', 1706111100000);

-- Projects (Token projects)
INSERT INTO project (id, entity_id, name, symbol, description, logo, lending_total) VALUES
('88888888-8888-8888-8888-888888888801', '33333333-3333-3333-3333-333333333305', 'Uniswap', 'UNI', 'Decentralized exchange protocol', 'https://tokens.example.com/uni.png', 5000000000),
('88888888-8888-8888-8888-888888888802', '33333333-3333-3333-3333-333333333309', 'Aave', 'AAVE', 'Decentralized lending protocol', 'https://tokens.example.com/aave.png', 12000000000),
('88888888-8888-8888-8888-888888888803', NULL, 'Chainlink', 'LINK', 'Decentralized oracle network', 'https://tokens.example.com/link.png', NULL),
('88888888-8888-8888-8888-888888888804', NULL, 'Dogecoin', 'DOGE', 'The original memecoin', 'https://tokens.example.com/doge.png', NULL),
('88888888-8888-8888-8888-888888888805', NULL, 'Shiba Inu', 'SHIB', 'Dogecoin killer memecoin', 'https://tokens.example.com/shib.png', NULL),
('88888888-8888-8888-8888-888888888806', '33333333-3333-3333-3333-333333333310', 'USD Coin', 'USDC', 'Circle stablecoin', 'https://tokens.example.com/usdc.png', NULL),
('88888888-8888-8888-8888-888888888807', NULL, 'Lido Staked Ether', 'stETH', 'Liquid staking token', 'https://tokens.example.com/steth.png', 28000000000),
('88888888-8888-8888-8888-888888888808', NULL, 'Arbitrum', 'ARB', 'Layer 2 governance token', 'https://tokens.example.com/arb.png', NULL),
('88888888-8888-8888-8888-888888888809', NULL, 'Optimism', 'OP', 'Layer 2 governance token', 'https://tokens.example.com/op.png', NULL),
('88888888-8888-8888-8888-888888888810', NULL, 'Pepe', 'PEPE', 'Frog memecoin', 'https://tokens.example.com/pepe.png', NULL);

-- Tokens (on-chain data)
INSERT INTO token (id, entity_id, project_id, chain_id, contract_address, decimals, name, symbol, logo, type, volume_24h, market_cap, price_usd, is_verified, price_change_24h, standard, network, is_native, is_mainstream) VALUES
('99999999-9999-9999-9999-999999999901', '33333333-3333-3333-3333-333333333305', '88888888-8888-8888-8888-888888888801', '22222222-2222-2222-2222-222222222201', '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 18, 'Uniswap', 'UNI', 'https://tokens.example.com/uni.png', 'governance', 250000000, 6500000000, 7.25, true, 2.5, 'ERC20', 'ethereum', false, true),
('99999999-9999-9999-9999-999999999902', '33333333-3333-3333-3333-333333333309', '88888888-8888-8888-8888-888888888802', '22222222-2222-2222-2222-222222222201', '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', 18, 'Aave', 'AAVE', 'https://tokens.example.com/aave.png', 'governance', 180000000, 4200000000, 95.50, true, -1.2, 'ERC20', 'ethereum', false, true),
('99999999-9999-9999-9999-999999999903', NULL, '88888888-8888-8888-8888-888888888803', '22222222-2222-2222-2222-222222222201', '0x514910771AF9Ca656af840dff83E8264EcF986CA', 18, 'Chainlink', 'LINK', 'https://tokens.example.com/link.png', 'utility', 520000000, 8900000000, 15.80, true, 3.8, 'ERC20', 'ethereum', false, true),
('99999999-9999-9999-9999-999999999904', NULL, '88888888-8888-8888-8888-888888888804', '22222222-2222-2222-2222-222222222202', '0xbA2aE424d960c26247Dd6c32edC70B295c744C43', 8, 'Dogecoin', 'DOGE', 'https://tokens.example.com/doge.png', 'meme', 850000000, 12000000000, 0.085, true, 5.2, 'BEP20', 'bsc', false, true),
('99999999-9999-9999-9999-999999999905', NULL, '88888888-8888-8888-8888-888888888805', '22222222-2222-2222-2222-222222222201', '0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE', 18, 'Shiba Inu', 'SHIB', 'https://tokens.example.com/shib.png', 'meme', 420000000, 5800000000, 0.0000098, true, 8.5, 'ERC20', 'ethereum', false, true),
('99999999-9999-9999-9999-999999999906', '33333333-3333-3333-3333-333333333310', '88888888-8888-8888-8888-888888888806', '22222222-2222-2222-2222-222222222201', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 6, 'USD Coin', 'USDC', 'https://tokens.example.com/usdc.png', 'stablecoin', 5200000000, 32000000000, 1.00, true, 0.01, 'ERC20', 'ethereum', false, true),
('99999999-9999-9999-9999-999999999907', NULL, '88888888-8888-8888-8888-888888888807', '22222222-2222-2222-2222-222222222201', '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84', 18, 'Lido Staked Ether', 'stETH', 'https://tokens.example.com/steth.png', 'liquid_staking', 150000000, 28000000000, 2450.00, true, 1.8, 'ERC20', 'ethereum', false, true),
('99999999-9999-9999-9999-999999999908', NULL, '88888888-8888-8888-8888-888888888808', '22222222-2222-2222-2222-222222222204', '0x912CE59144191C1204E64559FE8253a0e49E6548', 18, 'Arbitrum', 'ARB', 'https://tokens.example.com/arb.png', 'governance', 320000000, 2800000000, 1.15, true, -2.3, 'ERC20', 'arbitrum', false, true),
('99999999-9999-9999-9999-999999999909', NULL, '88888888-8888-8888-8888-888888888809', '22222222-2222-2222-2222-222222222205', '0x4200000000000000000000000000000000000042', 18, 'Optimism', 'OP', 'https://tokens.example.com/op.png', 'governance', 180000000, 2100000000, 2.35, true, 4.1, 'ERC20', 'optimism', false, true),
('99999999-9999-9999-9999-999999999910', NULL, '88888888-8888-8888-8888-888888888810', '22222222-2222-2222-2222-222222222201', '0x6982508145454Ce325dDbE47a25d4ec3d2311933', 18, 'Pepe', 'PEPE', 'https://tokens.example.com/pepe.png', 'meme', 680000000, 3200000000, 0.0000082, true, 12.5, 'ERC20', 'ethereum', false, false);

-- Entity Datasources (linking entities to twitter accounts)
INSERT INTO entity_datasource (id, entity_id, account_id, account_type, is_visible, account_slug, url) VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '33333333-3333-3333-3333-333333333301', '66666666-6666-6666-6666-666666666601', 'twitter', true, 'VitalikButerin', 'https://twitter.com/VitalikButerin'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa02', '33333333-3333-3333-3333-333333333302', '66666666-6666-6666-6666-666666666602', 'twitter', true, 'caborc', 'https://twitter.com/caborc'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa03', '33333333-3333-3333-3333-333333333306', '66666666-6666-6666-6666-666666666603', 'twitter', true, 'elonmusk', 'https://twitter.com/elonmusk'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa04', '33333333-3333-3333-3333-333333333307', '66666666-6666-6666-6666-666666666604', 'twitter', true, 'saborc', 'https://twitter.com/saborc'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa05', '33333333-3333-3333-3333-333333333305', '66666666-6666-6666-6666-666666666605', 'twitter', true, 'Uniswap', 'https://twitter.com/Uniswap'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa06', '33333333-3333-3333-3333-333333333303', '66666666-6666-6666-6666-666666666606', 'twitter', true, 'binance', 'https://twitter.com/binance'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa07', '33333333-3333-3333-3333-333333333304', '66666666-6666-6666-6666-666666666607', 'twitter', true, 'coinbase', 'https://twitter.com/coinbase'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa08', '33333333-3333-3333-3333-333333333308', '66666666-6666-6666-6666-666666666608', 'twitter', true, 'opensea', 'https://twitter.com/opensea'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa09', '33333333-3333-3333-3333-333333333309', '66666666-6666-6666-6666-666666666609', 'twitter', true, 'AaveAave', 'https://twitter.com/AaveAave'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa10', '33333333-3333-3333-3333-333333333310', '66666666-6666-6666-6666-666666666610', 'twitter', true, 'circle', 'https://twitter.com/circle');

-- Entity Tags (linking entities to tags)
INSERT INTO entity_tag (id, entity_id, tag_id, type) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb01', '33333333-3333-3333-3333-333333333301', '44444444-4444-4444-4444-444444444405', 'primary'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb02', '33333333-3333-3333-3333-333333333302', '44444444-4444-4444-4444-444444444409', 'primary'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb03', '33333333-3333-3333-3333-333333333303', '44444444-4444-4444-4444-444444444409', 'primary'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb04', '33333333-3333-3333-3333-333333333304', '44444444-4444-4444-4444-444444444409', 'primary'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb05', '33333333-3333-3333-3333-333333333305', '44444444-4444-4444-4444-444444444401', 'primary'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb06', '33333333-3333-3333-3333-333333333306', '44444444-4444-4444-4444-444444444407', 'secondary'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb07', '33333333-3333-3333-3333-333333333307', '44444444-4444-4444-4444-444444444404', 'primary'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb08', '33333333-3333-3333-3333-333333333308', '44444444-4444-4444-4444-444444444402', 'primary'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb09', '33333333-3333-3333-3333-333333333309', '44444444-4444-4444-4444-444444444401', 'primary'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb10', '33333333-3333-3333-3333-333333333310', '44444444-4444-4444-4444-444444444401', 'secondary');

-- Entity Intelligences (linking entities to intelligences)
INSERT INTO entity_intelligence (id, entity_id, intelligence_id, type, highest_increase_rate, warning_price_usd) VALUES
('cccccccc-cccc-cccc-cccc-cccccccccc01', '33333333-3333-3333-3333-333333333301', '77777777-7777-7777-7777-777777777701', 'author', 15.5, 0),
('cccccccc-cccc-cccc-cccc-cccccccccc02', '33333333-3333-3333-3333-333333333302', '77777777-7777-7777-7777-777777777702', 'author', 8.2, 0),
('cccccccc-cccc-cccc-cccc-cccccccccc03', '33333333-3333-3333-3333-333333333307', '77777777-7777-7777-7777-777777777704', 'author', 22.0, 45000),
('cccccccc-cccc-cccc-cccc-cccccccccc04', '33333333-3333-3333-3333-333333333305', '77777777-7777-7777-7777-777777777705', 'mentioned', 5.8, 7.5),
('cccccccc-cccc-cccc-cccc-cccccccccc05', '33333333-3333-3333-3333-333333333306', '77777777-7777-7777-7777-777777777707', 'mentioned', 120.5, 0.00001),
('cccccccc-cccc-cccc-cccc-cccccccccc06', '33333333-3333-3333-3333-333333333303', '77777777-7777-7777-7777-777777777702', 'mentioned', 0, 0),
('cccccccc-cccc-cccc-cccc-cccccccccc07', '33333333-3333-3333-3333-333333333309', '77777777-7777-7777-7777-777777777710', 'mentioned', -50.0, 100),
('cccccccc-cccc-cccc-cccc-cccccccccc08', '33333333-3333-3333-3333-333333333304', '77777777-7777-7777-7777-777777777709', 'mentioned', 0, 0),
('cccccccc-cccc-cccc-cccc-cccccccccc09', '33333333-3333-3333-3333-333333333301', '77777777-7777-7777-7777-777777777708', 'mentioned', 18.3, 0),
('cccccccc-cccc-cccc-cccc-cccccccccc10', '33333333-3333-3333-3333-333333333310', '77777777-7777-7777-7777-777777777706', 'mentioned', 0, 1.0);

-- Tag Intelligences (linking tags to intelligences)
INSERT INTO tag_intelligence (id, tag_id, intelligence_id, type) VALUES
('dddddddd-dddd-dddd-dddd-dddddddddd01', '44444444-4444-4444-4444-444444444405', '77777777-7777-7777-7777-777777777701', 'signal'),
('dddddddd-dddd-dddd-dddd-dddddddddd02', '44444444-4444-4444-4444-444444444409', '77777777-7777-7777-7777-777777777702', 'signal'),
('dddddddd-dddd-dddd-dddd-dddddddddd03', '44444444-4444-4444-4444-444444444410', '77777777-7777-7777-7777-777777777703', 'alert'),
('dddddddd-dddd-dddd-dddd-dddddddddd04', '44444444-4444-4444-4444-444444444404', '77777777-7777-7777-7777-777777777704', 'signal'),
('dddddddd-dddd-dddd-dddd-dddddddddd05', '44444444-4444-4444-4444-444444444401', '77777777-7777-7777-7777-777777777705', 'signal'),
('dddddddd-dddd-dddd-dddd-dddddddddd06', '44444444-4444-4444-4444-444444444404', '77777777-7777-7777-7777-777777777706', 'signal'),
('dddddddd-dddd-dddd-dddd-dddddddddd07', '44444444-4444-4444-4444-444444444407', '77777777-7777-7777-7777-777777777707', 'alpha'),
('dddddddd-dddd-dddd-dddd-dddddddddd08', '44444444-4444-4444-4444-444444444403', '77777777-7777-7777-7777-777777777708', 'signal'),
('dddddddd-dddd-dddd-dddd-dddddddddd09', '44444444-4444-4444-4444-444444444409', '77777777-7777-7777-7777-777777777709', 'news'),
('dddddddd-dddd-dddd-dddd-dddddddddd10', '44444444-4444-4444-4444-444444444401', '77777777-7777-7777-7777-777777777710', 'alert');

-- User Subsets (linking users to subsets)
INSERT INTO user_subset (id, user_id, subset_id) VALUES
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01', '11111111-1111-1111-1111-111111111101', '55555555-5555-5555-5555-555555555501'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee02', '11111111-1111-1111-1111-111111111101', '55555555-5555-5555-5555-555555555507'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee03', '11111111-1111-1111-1111-111111111102', '55555555-5555-5555-5555-555555555504'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee04', '11111111-1111-1111-1111-111111111103', '55555555-5555-5555-5555-555555555508'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee05', '11111111-1111-1111-1111-111111111104', '55555555-5555-5555-5555-555555555501'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee06', '11111111-1111-1111-1111-111111111105', '55555555-5555-5555-5555-555555555502'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee07', '11111111-1111-1111-1111-111111111106', '55555555-5555-5555-5555-555555555506'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee08', '11111111-1111-1111-1111-111111111107', '55555555-5555-5555-5555-555555555509'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee09', '11111111-1111-1111-1111-111111111108', '55555555-5555-5555-5555-555555555510'),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeee10', '11111111-1111-1111-1111-111111111109', '55555555-5555-5555-5555-555555555503');

-- AI Agents
INSERT INTO ai_agent (id, name, description, avatar, rank, subset_id, tag_id) VALUES
('ffffffff-ffff-ffff-ffff-ffffffffffff', '{"en": "DeFi Hunter", "zh": "DeFi猎手"}', '{"en": "Tracks DeFi opportunities", "zh": "追踪DeFi机会"}', 'https://avatar.example.com/defi-hunter.png', 1, '55555555-5555-5555-5555-555555555501', '44444444-4444-4444-4444-444444444401'),
('ffffffff-ffff-ffff-ffff-ffffffffff02', '{"en": "NFT Scout", "zh": "NFT侦察兵"}', '{"en": "Discovers NFT trends", "zh": "发现NFT趋势"}', 'https://avatar.example.com/nft-scout.png', 2, '55555555-5555-5555-5555-555555555502', '44444444-4444-4444-4444-444444444402'),
('ffffffff-ffff-ffff-ffff-ffffffffff03', '{"en": "L2 Watcher", "zh": "L2观察者"}', '{"en": "Monitors Layer 2 ecosystem", "zh": "监控Layer 2生态"}', 'https://avatar.example.com/l2-watcher.png', 3, '55555555-5555-5555-5555-555555555503', '44444444-4444-4444-4444-444444444403'),
('ffffffff-ffff-ffff-ffff-ffffffffff04', '{"en": "Bitcoin Sage", "zh": "比特币智者"}', '{"en": "Bitcoin analysis expert", "zh": "比特币分析专家"}', 'https://avatar.example.com/btc-sage.png', 4, '55555555-5555-5555-5555-555555555506', '44444444-4444-4444-4444-444444444404'),
('ffffffff-ffff-ffff-ffff-ffffffffff05', '{"en": "ETH Oracle", "zh": "以太坊预言家"}', '{"en": "Ethereum ecosystem tracker", "zh": "以太坊生态追踪"}', 'https://avatar.example.com/eth-oracle.png', 5, '55555555-5555-5555-5555-555555555507', '44444444-4444-4444-4444-444444444405'),
('ffffffff-ffff-ffff-ffff-ffffffffff06', '{"en": "Meme Master", "zh": "Meme大师"}', '{"en": "Meme coin analyst", "zh": "Meme币分析师"}', 'https://avatar.example.com/meme-master.png', 6, '55555555-5555-5555-5555-555555555508', '44444444-4444-4444-4444-444444444407'),
('ffffffff-ffff-ffff-ffff-ffffffffff07', '{"en": "CEX Monitor", "zh": "交易所监控"}', '{"en": "Exchange activity tracker", "zh": "交易所活动追踪"}', 'https://avatar.example.com/cex-monitor.png', 7, '55555555-5555-5555-5555-555555555505', '44444444-4444-4444-4444-444444444409'),
('ffffffff-ffff-ffff-ffff-ffffffffff08', '{"en": "GameFi Guide", "zh": "GameFi向导"}', '{"en": "Gaming and metaverse expert", "zh": "游戏和元宇宙专家"}', 'https://avatar.example.com/gamefi-guide.png', 8, '55555555-5555-5555-5555-555555555509', '44444444-4444-4444-4444-444444444408'),
('ffffffff-ffff-ffff-ffff-ffffffffff09', '{"en": "Reg Watch", "zh": "监管观察"}', '{"en": "Regulatory news tracker", "zh": "监管新闻追踪"}', 'https://avatar.example.com/reg-watch.png', 9, '55555555-5555-5555-5555-555555555510', '44444444-4444-4444-4444-444444444410'),
('ffffffff-ffff-ffff-ffff-ffffffffff10', '{"en": "Sol Tracker", "zh": "Solana追踪者"}', '{"en": "Solana ecosystem monitor", "zh": "Solana生态监控"}', 'https://avatar.example.com/sol-tracker.png', 10, NULL, '44444444-4444-4444-4444-444444444406');

-- News Platforms
INSERT INTO news_platform (id, name, content_type, extra_data, entity_id, type, interval) VALUES
('10101010-1010-1010-1010-101010101001', 'CoinDesk', 'article', '{"rss": "https://coindesk.com/feed"}', '33333333-3333-3333-3333-333333333303', 'news', '5m'),
('10101010-1010-1010-1010-101010101002', 'The Block', 'article', '{"rss": "https://theblock.co/feed"}', '33333333-3333-3333-3333-333333333304', 'news', '5m'),
('10101010-1010-1010-1010-101010101003', 'Decrypt', 'article', '{"rss": "https://decrypt.co/feed"}', NULL, 'news', '10m'),
('10101010-1010-1010-1010-101010101004', 'CryptoSlate', 'article', '{"rss": "https://cryptoslate.com/feed"}', NULL, 'news', '10m'),
('10101010-1010-1010-1010-101010101005', 'Cointelegraph', 'article', '{"rss": "https://cointelegraph.com/feed"}', NULL, 'news', '5m'),
('10101010-1010-1010-1010-101010101006', 'Bloomberg Crypto', 'article', '{"api": "bloomberg"}', NULL, 'news', '15m'),
('10101010-1010-1010-1010-101010101007', 'Reuters Crypto', 'article', '{"api": "reuters"}', NULL, 'news', '15m'),
('10101010-1010-1010-1010-101010101008', 'Messari', 'research', '{"api": "messari"}', NULL, 'research', '1h'),
('10101010-1010-1010-1010-101010101009', 'Delphi Digital', 'research', '{"api": "delphi"}', NULL, 'research', '1h'),
('10101010-1010-1010-1010-101010101010', 'Bankless', 'newsletter', '{"substack": "bankless"}', NULL, 'newsletter', '1d');

-- Exchange Platforms
INSERT INTO exchange_platform (id, entity_id, type, name, content_type, interval, extra_data) VALUES
('20202020-2020-2020-2020-202020202001', '33333333-3333-3333-3333-333333333303', 'cex', 'Binance', 'announcement', '1m', '{"api_base": "https://api.binance.com"}'),
('20202020-2020-2020-2020-202020202002', '33333333-3333-3333-3333-333333333304', 'cex', 'Coinbase', 'announcement', '1m', '{"api_base": "https://api.coinbase.com"}'),
('20202020-2020-2020-2020-202020202003', NULL, 'cex', 'Kraken', 'announcement', '5m', '{"api_base": "https://api.kraken.com"}'),
('20202020-2020-2020-2020-202020202004', NULL, 'cex', 'OKX', 'announcement', '1m', '{"api_base": "https://www.okx.com/api"}'),
('20202020-2020-2020-2020-202020202005', NULL, 'cex', 'Bybit', 'announcement', '5m', '{"api_base": "https://api.bybit.com"}'),
('20202020-2020-2020-2020-202020202006', NULL, 'cex', 'KuCoin', 'announcement', '5m', '{"api_base": "https://api.kucoin.com"}'),
('20202020-2020-2020-2020-202020202007', '33333333-3333-3333-3333-333333333305', 'dex', 'Uniswap', 'pool_creation', '1m', '{"subgraph": "uniswap-v3"}'),
('20202020-2020-2020-2020-202020202008', NULL, 'dex', 'SushiSwap', 'pool_creation', '5m', '{"subgraph": "sushiswap"}'),
('20202020-2020-2020-2020-202020202009', NULL, 'dex', 'Curve', 'pool_creation', '5m', '{"subgraph": "curve"}'),
('20202020-2020-2020-2020-202020202010', NULL, 'dex', 'PancakeSwap', 'pool_creation', '1m', '{"subgraph": "pancakeswap"}');

-- Token Social Links
INSERT INTO token_social_links (id, network, contract_address, link_type, url, rank) VALUES
('30303030-3030-3030-3030-303030303001', 'ethereum', '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 'twitter', 'https://twitter.com/Uniswap', 1),
('30303030-3030-3030-3030-303030303002', 'ethereum', '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 'website', 'https://uniswap.org', 2),
('30303030-3030-3030-3030-303030303003', 'ethereum', '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', 'twitter', 'https://twitter.com/AaveAave', 1),
('30303030-3030-3030-3030-303030303004', 'ethereum', '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', 'website', 'https://aave.com', 2),
('30303030-3030-3030-3030-303030303005', 'ethereum', '0x514910771AF9Ca656af840dff83E8264EcF986CA', 'twitter', 'https://twitter.com/chainlink', 1),
('30303030-3030-3030-3030-303030303006', 'ethereum', '0x514910771AF9Ca656af840dff83E8264EcF986CA', 'website', 'https://chain.link', 2),
('30303030-3030-3030-3030-303030303007', 'ethereum', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 'twitter', 'https://twitter.com/circle', 1),
('30303030-3030-3030-3030-303030303008', 'ethereum', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 'website', 'https://circle.com/usdc', 2),
('30303030-3030-3030-3030-303030303009', 'ethereum', '0x6982508145454Ce325dDbE47a25d4ec3d2311933', 'twitter', 'https://twitter.com/pepecoineth', 1),
('30303030-3030-3030-3030-303030303010', 'ethereum', '0x6982508145454Ce325dDbE47a25d4ec3d2311933', 'telegram', 'https://t.me/pepecoineth', 3);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_intelligence_published_at ON intelligence(published_at);
CREATE INDEX IF NOT EXISTS idx_intelligence_type ON intelligence(type);
CREATE INDEX IF NOT EXISTS idx_token_symbol ON token(symbol);
CREATE INDEX IF NOT EXISTS idx_token_chain_id ON token(chain_id);
CREATE INDEX IF NOT EXISTS idx_entity_type ON entity(type);
CREATE INDEX IF NOT EXISTS idx_user_tid ON "user"(tid);
