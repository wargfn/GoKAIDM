// GoKAIDM MCP server – Adobe Firefly image generation tools.
//
// Required environment variables:
//
//	FIREFLY_CLIENT_ID     – Adobe Developer Console client ID
//	FIREFLY_CLIENT_SECRET – Adobe Developer Console client secret
//
// Start the server (stdio transport, compatible with Claude Desktop and similar
// MCP hosts):
//
//	FIREFLY_CLIENT_ID=... FIREFLY_CLIENT_SECRET=... ./GoKAIDM
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"github.com/wargfn/GoKAIDM/firefly"
)

func main() {
	clientID := os.Getenv("FIREFLY_CLIENT_ID")
	clientSecret := os.Getenv("FIREFLY_CLIENT_SECRET")
	if clientID == "" || clientSecret == "" {
		fmt.Fprintln(os.Stderr, "error: FIREFLY_CLIENT_ID and FIREFLY_CLIENT_SECRET must be set")
		os.Exit(1)
	}

	ff := firefly.NewClient(clientID, clientSecret)

	s := server.NewMCPServer(
		"GoKAIDM Firefly",
		"1.0.0",
		server.WithToolCapabilities(false),
	)

	// ── generate_image ────────────────────────────────────────────────────────
	generateTool := mcp.NewTool("generate_image",
		mcp.WithDescription(
			"Generate one or more images from a text prompt using Adobe Firefly. "+
				"Returns a JSON array of objects each containing a presigned image URL and a seed."),
		mcp.WithString("prompt",
			mcp.Required(),
			mcp.Description("Text description of the desired image (max ~1 000 characters)."),
		),
		mcp.WithString("negative_prompt",
			mcp.Description("Things to exclude from the generated image."),
		),
		mcp.WithNumber("num_variations",
			mcp.Description("Number of image variants to generate (1–4). Defaults to 1."),
		),
		mcp.WithString("content_class",
			mcp.Description(`Visual content class: "photo" or "art". Defaults to "photo".`),
		),
		mcp.WithNumber("width",
			mcp.Description("Image width in pixels. Must form a supported aspect ratio with height. Defaults to 1024."),
		),
		mcp.WithNumber("height",
			mcp.Description("Image height in pixels. Must form a supported aspect ratio with width. Defaults to 1024."),
		),
		mcp.WithString("style_presets",
			mcp.Description(`Comma-separated Firefly style preset names, e.g. "photo,studio_shot".`),
		),
		mcp.WithNumber("style_strength",
			mcp.Description("How strongly the style presets are applied (1–100). Defaults to 60."),
		),
		mcp.WithNumber("seed",
			mcp.Description("Seed value to reproduce a specific image. Omit for a random result."),
		),
	)
	s.AddTool(generateTool, generateHandler(ff))

	if err := server.ServeStdio(s); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}

// generateHandler returns a CallToolHandler that drives the Firefly generate API.
func generateHandler(ff *firefly.Client) server.ToolHandlerFunc {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		prompt, err := req.RequireString("prompt")
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		genReq := firefly.GenerateRequest{
			Prompt:       prompt,
			NumVariations: 1,
		}

		if v := req.GetString("negative_prompt", ""); v != "" {
			genReq.NegativePrompt = v
		}
		if v := req.GetInt("num_variations", 1); v >= 1 {
			genReq.NumVariations = v
		}
		if v := req.GetString("content_class", ""); v != "" {
			genReq.ContentClass = v
		}

		width := req.GetInt("width", 1024)
		height := req.GetInt("height", 1024)
		genReq.Size = &firefly.Size{Width: width, Height: height}

		// Style
		if presets := req.GetString("style_presets", ""); presets != "" {
			style := &firefly.Style{}
			for _, p := range strings.Split(presets, ",") {
				p = strings.TrimSpace(p)
				if p != "" {
					style.Presets = append(style.Presets, firefly.StylePreset(p))
				}
			}
			if v := req.GetInt("style_strength", 0); v > 0 {
				style.Strength = v
			}
			if len(style.Presets) > 0 {
				genReq.Style = style
			}
		}

		// Seed
		if v := req.GetInt("seed", 0); v > 0 {
			genReq.Seeds = []int{v}
		}

		resp, err := ff.GenerateImage(ctx, genReq)
		if err != nil {
			return mcp.NewToolResultError(fmt.Sprintf("Firefly API error: %v", err)), nil
		}

		// Return structured JSON so the host can render / link the images.
		type outputItem struct {
			Seed         int    `json:"seed"`
			URL          string `json:"url"`
			PresignedURL string `json:"presigned_url"`
		}
		items := make([]outputItem, 0, len(resp.Outputs))
		for _, o := range resp.Outputs {
			items = append(items, outputItem{
				Seed:         o.Seed,
				URL:          o.Image.URL,
				PresignedURL: o.Image.PresignedURL,
			})
		}

		out, err := json.MarshalIndent(items, "", "  ")
		if err != nil {
			return mcp.NewToolResultError("failed to encode response"), nil
		}

		return mcp.NewToolResultText(string(out)), nil
	}
}
