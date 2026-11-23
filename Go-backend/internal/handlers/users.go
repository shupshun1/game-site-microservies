package handlers

import (
	"encoding/json"
	"log/slog"
	"net/http"

	"game-site-backend/internal/auth"
	"game-site-backend/internal/models"
	"game-site-backend/internal/storage"

	"golang.org/x/crypto/bcrypt"
)

type Handler struct {
	Storage *storage.Storage
}

func New(s *storage.Storage) *Handler {
	return &Handler{Storage: s}
}

func (h *Handler) Register(w http.ResponseWriter, r *http.Request) {
	if meth := r.Method; meth != http.MethodPost {
		http.Error(w, "Method is not allowed", http.StatusMethodNotAllowed)
		return
	}

	var request models.RegisterRequest

	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		slog.Error("Could not decode register attempt", "err", err)
		http.Error(w, "Invalid JSON format", http.StatusBadRequest)
		return
	}

	if len(request.Username) < 2 {
		http.Error(w, "username must be at least 2 characters", http.StatusBadRequest)
		return
	}

	if len(request.Password) < 6 {
		http.Error(w, "Password must be at least 6 characters", http.StatusBadRequest)
		return
	}

	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(request.Password), bcrypt.DefaultCost)
	if err != nil {
		slog.Error("Failed to hash password", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	user, err := h.Storage.CreateUser(r.Context(), request.Username, string(hashedPassword))
	if err != nil {
		slog.Error("Could not create user", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	token, err := auth.GenerateToken(user.ID, user.Username)
	if err != nil {
		slog.Error("Failed to generate JWT token", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	resp := models.RegisterResponse{
		Status:  "ok",
		UserId:  user.ID,
		Token:   token,
		Message: "User created successfully",
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)

	if err = json.NewEncoder(w).Encode(resp); err != nil {
		slog.Error("Failed to encode response", "err", err)
		return
	}
}

func (h *Handler) Login(w http.ResponseWriter, r *http.Request) {
	if meth := r.Method; meth != http.MethodPost {
		http.Error(w, "Method is not allowed", http.StatusMethodNotAllowed)
		return
	}

	var request models.LoginRequest

	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		slog.Error("Could not decode login attempt", "err", err)
		http.Error(w, "Invalid JSON format", http.StatusBadRequest)
		return
	}

	user, err := h.Storage.GetUserByUsername(r.Context(), request.Username)
	if err != nil {
		slog.Error("Invalid username or password", "err", err)
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	if err = bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(request.Password)); err != nil {
		slog.Error("Invalid password", "err", err)
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	token, err := auth.GenerateToken(user.ID, user.Username)
	if err != nil {
		slog.Error("Failed to generate JWT token", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	resp := models.LoginResponse{
		Status: "ok",
		Token:  token,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	if err = json.NewEncoder(w).Encode(resp); err != nil {
		slog.Error("Failed to encode response", "err", err)
		return
	}
}

func (h *Handler) BuySkin(w http.ResponseWriter, r *http.Request) {
	userId := r.Context().Value("user_id").(int)

	var req models.BuySkinRequest
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		slog.Error("Could not decode purchase attempt", "err", err)
		http.Error(w, "Invalid JSON format", http.StatusBadRequest)
		return
	}

	err = h.Storage.BuySkin(r.Context(), userId, req.SkinId)
	if err != nil {
		slog.Error("Could not purchase a skin", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	resp := models.BuySkinResponse{
		Status: "ok",
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	if err := json.NewEncoder(w).Encode(resp); err != nil {
		slog.Error("Failed to encode response", "err", err)
		return
	}
}

func (h *Handler) GetProfile(w http.ResponseWriter, r *http.Request) {
	userId := r.Context().Value("user_id").(int)

	data, err := h.Storage.GetUserWithStats(r.Context(), userId)
	if err != nil {
		slog.Error("Could not get data", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	if err := json.NewEncoder(w).Encode(data); err != nil {
		slog.Error("Failed to encode response", "err", err)
		return
	}

}

func (h *Handler) UpdateStats(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("user_id").(int)

	var req models.UpdateStatsRequest

	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		slog.Error("Could not decode json", "err", err)
		http.Error(w, "Bad request", http.StatusBadRequest)
		return
	}

	err = h.Storage.UpdateStats(r.Context(), userID, req)
	if err != nil {
		slog.Error("Could not update stats", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	data, err := h.Storage.GetUserWithStats(r.Context(), userID)
	if err != nil {
		slog.Error("Could not get updated stats", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	if err := json.NewEncoder(w).Encode(data); err != nil {
		slog.Error("Failed to encode response", "err", err)
		return
	}
}

func (h *Handler) GetLeaderboard(w http.ResponseWriter, r *http.Request) {
	leaderboard, err := h.Storage.GetLeaderboardByBalance(r.Context())
	if err != nil {
		slog.Error("Could not get a leaderboard", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	if err := json.NewEncoder(w).Encode(leaderboard); err != nil {
		slog.Error("Failed to encode response", "err", err)
		return
	}
}

func (h *Handler) SetActiveSkin(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("user_id").(int)

	var req models.SetActiveSkinRequest

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		slog.Error("Could not decode json", "err", err)
		http.Error(w, "Bad request", http.StatusBadRequest)
		return
	}

	err := h.Storage.SetActiveSkin(r.Context(), userID, req.SkinName)
	if err != nil {
		slog.Error("Could not set active skin", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	resp := models.SetActiveSkinResponse{
		Status: "ok",
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	if err := json.NewEncoder(w).Encode(resp); err != nil {
		slog.Error("Failed to encode response", "err", err)
		return
	}
}

func (h *Handler) UpdateUserProfile(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("user_id").(int)

	var req models.UpdateProfileRequest

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		slog.Error("Could not decode json", "err", err)
		http.Error(w, "Bad request", http.StatusBadRequest)
		return
	}

	if len(req.Username) < 2 {
		http.Error(w, "username must be at least 2 characters", http.StatusBadRequest)
		return
	}

	if err := h.Storage.UpdateUserProfile(r.Context(), userID, req.Username, req.PhotoUrl); err != nil {
		slog.Error("Could not update profile data", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	resp := models.UpdateProfileResponse{
		Status: "ok",
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	if err := json.NewEncoder(w).Encode(resp); err != nil {
		slog.Error("Failed to encode response", "err", err)
		return
	}
}

func (h *Handler) ChangePassword(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("user_id").(int)

	var req models.ChangePasswordRequest

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		slog.Error("Could not decode login attempt", "err", err)
		http.Error(w, "Invalid JSON format", http.StatusBadRequest)
		return
	}

	if len(req.NewPassword) < 6 {
		http.Error(w, "Password must be at least 6 characters", http.StatusBadRequest)
		return
	}

	NewHashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.NewPassword), bcrypt.DefaultCost)
	if err != nil {
		slog.Error("Failed to hash password", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	if err := h.Storage.UpdateUserPassword(r.Context(), userID, string(NewHashedPassword)); err != nil {
		slog.Error("Could not update password", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	resp := models.ChangePasswordResponse{
		Status: "ok",
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	if err := json.NewEncoder(w).Encode(resp); err != nil {
		slog.Error("Failed to encode response", "err", err)
		return
	}
}
