CREATE TABLE IF NOT EXISTS `warns` (
  `id` int(11) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ギルドごとのVC設定
CREATE TABLE IF NOT EXISTS `guild_vc_settings` (
  `guild_id` TEXT PRIMARY KEY,
  `base_name_template` TEXT NOT NULL DEFAULT '{user_name}のVC',
  `name_counter` INTEGER NOT NULL DEFAULT 0,
  `max_channels` INTEGER NOT NULL DEFAULT 50,
  `delete_delay` INTEGER NOT NULL DEFAULT 30,
  `log_channel_id` TEXT
);

-- /vc create で作られたベースVCの記録
CREATE TABLE IF NOT EXISTS `vc_base_channels` (
  `channel_id` TEXT PRIMARY KEY,
  `guild_id` TEXT NOT NULL,
  `creator_id` TEXT,
  `name_template` TEXT,
  `name_counter` INTEGER NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Botが自動生成した複製VCの記録
CREATE TABLE IF NOT EXISTS `vc_generated_channels` (
  `channel_id` TEXT PRIMARY KEY,
  `guild_id` TEXT NOT NULL,
  `base_channel_id` TEXT NOT NULL,
  `creator_id` TEXT,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_at` TIMESTAMP
);

-- パフォーマンス向上のためのインデックス
CREATE INDEX IF NOT EXISTS `idx_vc_generated_guild_active`
ON `vc_generated_channels` (`guild_id`, `deleted_at`);

CREATE INDEX IF NOT EXISTS `idx_vc_base_guild`
ON `vc_base_channels` (`guild_id`);