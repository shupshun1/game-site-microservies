package models

import (
	"time"
)

// DB models

type User struct {
	ID        int       `json:"id"`
	Username  string    `json:"username"`
	PhotoUrl  string    `json:"photo_url"`
	CreatedAt time.Time `json:"created_at"`
}

type UserStats struct {
	ID             int `json:"id"`
	UserId         int `json:"user_id"`
	Kills          int `json:"kills"`
	Deaths         int `json:"deaths"`
	BossesDefeated int `json:"bosses_defeated"`
	TotalWave      int `json:"total_wave"`
	EnemiesKilled  int `json:"enemies_killed"`
	SwordsThrown   int `json:"swords_thrown"`
	SwordsMissed   int `json:"swords_missed"`
	SwordsHitted   int `json:"swords_hitted"`
	Balance        int `json:"balance"`
}

type UserSkins struct {
	ID         int    `json:"id"`
	UserId     int    `json:"user_id"`
	OwnedSkins int    `json:"owned_skins"`
	ActiveSkin string `json:"active_skin"`
}

// Request and Response

type RegisterRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type RegisterResponse struct {
	Status  string `json:"status"`
	UserId  int    `json:"user_id"`
	Message string `json:"message"`
}

type LoginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type LoginResponse struct {
	Status string `json:"status"`
	Token  string `json:"token"`
}

type BuySkinRequest struct {
	SkinId int `json:"skin_id"`
}

type BuySkinResponse struct {
	Status  string `json:"status"`
	Balance int    `json:"balance"`
}
