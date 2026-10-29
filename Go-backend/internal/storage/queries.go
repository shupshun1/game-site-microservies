package storage

import (
	"context"
	"fmt"
	"game-site-backend/internal/models"
	"log/slog"
)

func (s *Storage) CreateUser(ctx context.Context, username, passwordHash string) (*models.User, error) {
	// Start transaction
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		slog.Error("Could not create a transaction")
		return nil, err
	}
	defer tx.Rollback()

	var user models.User

	err = tx.QueryRowContext(ctx, `INSERT INTO users (username, password_hash) 
	VALUES ($1, $2) 
	RETURNING id, username, photo_url, created_at`, username, passwordHash).Scan(&user.ID, &user.Username, &user.PhotoUrl, &user.CreatedAt)
	if err != nil {
		slog.Error("Could not create a new user", "err", err)
		return nil, err
	}

	_, err = tx.ExecContext(ctx, `INSERT INTO users_stats (user_id) VALUES ($1)`, user.ID)
	if err != nil {
		slog.Error("Could not insert a new user into user_stats", "err", err)
		return nil, err
	}

	_, err = tx.ExecContext(ctx, `INSERT INTO users_skins (user_id) VALUES($1)`, user.ID)
	if err != nil {
		slog.Error("Could not insert a new user into users_skins", "err", err)
		return nil, err
	}

	if err = tx.Commit(); err != nil {
		slog.Error("Could not commit transaction", "err", err)
		return nil, err
	}

	return &user, nil
}

func (s *Storage) GetUserByUsername(ctx context.Context, username string) (*models.User, error) {
	var user models.User

	err := s.db.QueryRowContext(ctx, `SELECT id, username, password_hash, photo_url, created_at
	FROM users
	WHERE username = $1`, username).Scan(&user.ID, &user.Username, &user.PasswordHash, &user.PhotoUrl, &user.CreatedAt)

	if err != nil {
		slog.Error("Could not take user by username from users", "err", err)
		return nil, err
	}

	return &user, nil
}

func (s *Storage) GetUserByID(ctx context.Context, userId int) (*models.User, error) {
	var user models.User

	err := s.db.QueryRowContext(ctx, `SELECT id, username, photo_url, created_at FROM users WHERE id = $1`, userId).Scan(&user.ID, &user.Username, &user.PhotoUrl, &user.CreatedAt)

	if err != nil {
		slog.Error("Could not take user by ID from user", "err", err)
		return nil, err
	}

	return &user, nil
}

func (s *Storage) GetUserWithStats(ctx context.Context, userID int) (*models.UserWithStats, error) {
	var data models.UserWithStats

	query := `
		SELECT 
			u.username, 
			s.kills, s.deaths, s.bosses_defeated, s.total_wave, 
			s.enemies_killed, s.swords_thrown, s.swords_missed, 
			s.swords_hitted, s.balance,
			sk.active_skin, sk.owned_skins
		FROM users u
		JOIN users_stats s ON u.id = s.user_id
		JOIN users_skins sk ON u.id = sk.user_id
		WHERE u.id = $1
	`

	err := s.db.QueryRowContext(ctx, query, userID).Scan(
		&data.Username,
		&data.Kills, &data.Deaths, &data.BossesDefeated, &data.TotalWave,
		&data.EnemiesKilled, &data.SwordsThrown, &data.SwordsMissed,
		&data.SwordsHitted, &data.Balance,
		&data.ActiveSkin, &data.OwnedSkins,
	)

	if err != nil {
		slog.Error("Could not get user with stats", "err", err)
		return nil, err
	}

	return &data, nil
}

func (s *Storage) UpdateStats(ctx context.Context, userID int, stats models.UpdateStatsRequest) error {
	query := `
		UPDATE users_stats SET kills = kills + $1, 
		deaths = deaths + $2,
		bosses_defeated = bosses_defeated + $3,
		total_wave = total_wave + $4,
		enemies_killed = enemies_killed + $5,
		swords_thrown = swords_thrown + $6,
		swords_missed = swords_missed + $7,
		swords_hitted = swords_hitted + $8,
		balance = balance + $9
		WHERE user_id = $10
	`
	res, err := s.db.ExecContext(ctx, query, stats.Kills, stats.Deaths, stats.BossesDefeated,
		stats.TotalWave, stats.EnemiesKilled, stats.SwordsThrown, stats.SwordsMissed,
		stats.SwordsHitted, stats.Balance, userID)

	if err != nil {
		slog.Error("Could not update stats", "err", err)
		return err
	}

	count, err := res.RowsAffected()
	if err != nil {
		slog.Error("Could not update stats", "err", err)
		return err
	}

	if count == 0 {
		err := fmt.Errorf("user with id %d not found", userID)
		slog.Warn("Stats not updated: user not found", "user_id", userID)
		return err
	}

	return nil
}

func (s *Storage) GetLeaderboardByBalance(ctx context.Context) ([]models.UserWithStats, error) {
	query := `
        SELECT 
            u.username, 
            s.kills, s.deaths, s.bosses_defeated, s.total_wave, 
            s.enemies_killed, s.swords_thrown, s.swords_missed, 
            s.swords_hitted, s.balance,
            sk.active_skin, sk.owned_skins
        FROM users u
        JOIN users_stats s ON u.id = s.user_id
        JOIN users_skins sk ON u.id = sk.user_id
        ORDER BY s.balance DESC
        LIMIT 10
    `

	rows, err := s.db.QueryContext(ctx, query)
	if err != nil {
		slog.Error("Could not get stats from users_stats", "err", err)
		return nil, err
	}
	defer rows.Close()

	var leaderboard []models.UserWithStats

	for rows.Next() {
		var data models.UserWithStats

		err := rows.Scan(
			&data.Username,
			&data.Kills, &data.Deaths, &data.BossesDefeated, &data.TotalWave,
			&data.EnemiesKilled, &data.SwordsThrown, &data.SwordsMissed,
			&data.SwordsHitted, &data.Balance,
			&data.ActiveSkin, &data.OwnedSkins,
		)

		if err != nil {
			slog.Error("Could not scan leaderboard row", "err", err)
			return nil, err
		}

		leaderboard = append(leaderboard, data)
	}

	if err := rows.Err(); err != nil {
		slog.Error("Rows iteration error", "err", err)
		return nil, err
	}

	return leaderboard, nil
}

func (s *Storage) BuySkin(ctx context.Context, userID, skinID int) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		slog.Error("Could not create a transaction", "err", err)
		return err
	}
	defer tx.Rollback()

	const skinPrice = 10000

	var balance int
	var ownedSkins int

	err = tx.QueryRowContext(ctx,
		`SELECT st.balance, sk.owned_skins FROM
		users_stats st JOIN users_skins sk ON st.user_id = sk.user_id
		WHERE user_id = $1
		FOR UPDATE`, userID).Scan(&balance, &ownedSkins)
	if err != nil {
		slog.Error("Could not find a user")
		return err
	}

	if ownedSkins >= 2 {
		return fmt.Errorf("Skin is already owned")
	}

	if balance < skinPrice {
		return fmt.Errorf("Not enough balance")
	}

	_, err = tx.ExecContext(ctx, `
	UPDATE users_stats SET balance = balance - $1
	WHERE user_id = $2
	`, skinPrice, userID)

	if err != nil {
		slog.Error("Could not update balance", "err", err)
		return err
	}

	_, err = tx.ExecContext(ctx, `
	UPDATE users_skins SET owned_skins = 2
	WHERE user_id = $1
	`, userID)

	if err != nil {
		slog.Error("Could not update owned_skins", "err", err)
		return err
	}

	if err = tx.Commit(); err != nil {
		slog.Error("Could not commit the transaction", "err", err)
		return err
	}

	return nil
}
