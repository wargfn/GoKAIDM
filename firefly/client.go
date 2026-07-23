// Package firefly provides a client for the Adobe Firefly image generation API.
// It handles OAuth 2.0 token acquisition via Adobe IMS and exposes a simple
// GenerateImage method for text-to-image generation.
package firefly

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

const (
	imsTokenURL  = "https://ims-na1.adobelogin.com/ims/token/v3"
	fireflyAPIURL = "https://firefly-api.adobe.io"
	oauthScope   = "openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis"
)

// Client is a thread-safe Adobe Firefly API client.
type Client struct {
	clientID     string
	clientSecret string
	httpClient   *http.Client

	mu          sync.Mutex
	accessToken string
	tokenExpiry time.Time
}

// NewClient creates a new Firefly client using the given credentials.
func NewClient(clientID, clientSecret string) *Client {
	return &Client{
		clientID:     clientID,
		clientSecret: clientSecret,
		httpClient:   &http.Client{Timeout: 60 * time.Second},
	}
}

// token returns a valid access token, refreshing it if necessary.
func (c *Client) token(ctx context.Context) (string, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.accessToken != "" && time.Now().Before(c.tokenExpiry) {
		return c.accessToken, nil
	}

	form := url.Values{}
	form.Set("grant_type", "client_credentials")
	form.Set("client_id", c.clientID)
	form.Set("client_secret", c.clientSecret)
	form.Set("scope", oauthScope)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, imsTokenURL,
		strings.NewReader(form.Encode()))
	if err != nil {
		return "", fmt.Errorf("firefly: build token request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("firefly: fetch token: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("firefly: read token body: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("firefly: token request failed (%d): %s", resp.StatusCode, body)
	}

	var tr TokenResponse
	if err := json.Unmarshal(body, &tr); err != nil {
		return "", fmt.Errorf("firefly: decode token response: %w", err)
	}

	c.accessToken = tr.AccessToken
	// Subtract a 60-second buffer so we refresh before actual expiry.
	c.tokenExpiry = time.Now().Add(time.Duration(tr.ExpiresIn-60) * time.Second)

	return c.accessToken, nil
}

// GenerateImage calls POST /v3/images/generate and returns the response.
func (c *Client) GenerateImage(ctx context.Context, genReq GenerateRequest) (*GenerateResponse, error) {
	token, err := c.token(ctx)
	if err != nil {
		return nil, err
	}

	payload, err := json.Marshal(genReq)
	if err != nil {
		return nil, fmt.Errorf("firefly: encode request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		fireflyAPIURL+"/v3/images/generate", bytes.NewReader(payload))
	if err != nil {
		return nil, fmt.Errorf("firefly: build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("x-api-key", c.clientID)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("firefly: send request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("firefly: read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		var apiErr APIError
		if json.Unmarshal(body, &apiErr) == nil && apiErr.ErrorCode != "" {
			return nil, &apiErr
		}
		return nil, fmt.Errorf("firefly: API error (%d): %s", resp.StatusCode, body)
	}

	var genResp GenerateResponse
	if err := json.Unmarshal(body, &genResp); err != nil {
		return nil, fmt.Errorf("firefly: decode response: %w", err)
	}

	return &genResp, nil
}
