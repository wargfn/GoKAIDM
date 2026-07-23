package firefly

// TokenResponse holds the OAuth 2.0 access token returned by Adobe IMS.
type TokenResponse struct {
	AccessToken string `json:"access_token"`
	TokenType   string `json:"token_type"`
	ExpiresIn   int    `json:"expires_in"`
}

// Size represents the width and height of a generated image.
type Size struct {
	Width  int `json:"width"`
	Height int `json:"height"`
}

// StylePreset is one of the style preset identifiers supported by Firefly.
type StylePreset string

// Style controls the visual style applied to generated images.
type Style struct {
	Presets  []StylePreset `json:"presets,omitempty"`
	Strength int           `json:"strength,omitempty"`
}

// GenerateRequest is the body sent to POST /v3/images/generate.
type GenerateRequest struct {
	Prompt         string `json:"prompt"`
	NegativePrompt string `json:"negativePrompt,omitempty"`
	NumVariations  int    `json:"numVariations,omitempty"`
	// ContentClass is "photo" or "art".
	ContentClass string `json:"contentClass,omitempty"`
	Size         *Size  `json:"size,omitempty"`
	Style        *Style `json:"style,omitempty"`
	// Seeds allows reproducing a prior result.
	Seeds  []int  `json:"seeds,omitempty"`
	Locale string `json:"locale,omitempty"`
}

// ImageOutput holds a single generated image returned by the API.
type ImageOutput struct {
	Seed  int `json:"seed"`
	Image struct {
		URL          string `json:"url"`
		PresignedURL string `json:"presignedUrl"`
	} `json:"image"`
}

// GenerateResponse is the body returned by POST /v3/images/generate.
type GenerateResponse struct {
	Version string        `json:"version"`
	Size    Size          `json:"size"`
	Prompt  string        `json:"prompt"`
	Outputs []ImageOutput `json:"outputs"`
}

// APIError is an error payload returned by the Firefly API.
type APIError struct {
	ErrorCode string `json:"error_code"`
	Message   string `json:"message"`
}

func (e *APIError) Error() string {
	return e.ErrorCode + ": " + e.Message
}
