CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(30) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    photo_url VARCHAR(255) DEFAULT 'default.png',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users_stats (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    kills INT DEFAULT 0,
    deaths INT DEFAULT 0,
    bosses_defeated INT DEFAULT 0,
    total_wave INT DEFAULT 0,
    enemies_killed INT DEFAULT 0,
    swords_thrown INT DEFAULT 0,
    swords_missed INT DEFAULT 0,
    swords_hitted INT DEFAULT 0,
    balance INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users_skins (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    owned_skins INT DEFAULT 1,
    active_skin VARCHAR(30) DEFAULT 'brave knight'
);