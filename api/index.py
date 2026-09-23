from flask import Flask, request, jsonify, render_template_string, Response, stream_with_context
import yt_dlp
import requests
import json
import re
import os
import time
from urllib.parse import urlparse, quote, unquote

app = Flask(__name__)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="referrer" content="no-referrer">
    <title>Universal Video Downloader | Cross-Platform HD Downloads</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #090d16;
            --bg-card: rgba(18, 24, 38, 0.75);
            --bg-card-hover: rgba(26, 35, 54, 0.85);
            --border-glass: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(99, 102, 241, 0.4);
            --primary: #6366f1;
            --primary-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%);
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-base);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 32px 16px 64px;
            overflow-x: hidden;
            position: relative;
        }

        /* Ambient Glow Backgrounds */
        .ambient-glow {
            position: fixed;
            border-radius: 50%;
            filter: blur(120px);
            pointer-events: none;
            z-index: 0;
            opacity: 0.45;
        }

        .glow-1 {
            width: 480px;
            height: 480px;
            top: -120px;
            left: -100px;
            background: radial-gradient(circle, #4f46e5 0%, rgba(79, 70, 229, 0) 70%);
        }

        .glow-2 {
            width: 520px;
            height: 520px;
            bottom: -150px;
            right: -120px;
            background: radial-gradient(circle, #d946ef 0%, rgba(217, 70, 239, 0) 70%);
        }

        .glow-3 {
            width: 380px;
            height: 380px;
            top: 40%;
            left: 55%;
            background: radial-gradient(circle, #06b6d4 0%, rgba(6, 182, 212, 0) 70%);
            opacity: 0.25;
        }

        /* Container */
        .wrapper {
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 860px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 28px;
        }

        /* Header */
        header {
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }

        .brand-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 16px;
            background: rgba(99, 102, 241, 0.12);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 100px;
            font-size: 13px;
            font-weight: 600;
            color: #a5b4fc;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            backdrop-filter: blur(8px);
        }

        .brand-badge span.pulse-dot {
            width: 8px;
            height: 8px;
            background-color: #22c55e;
            border-radius: 50%;
            box-shadow: 0 0 10px #22c55e;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 44px;
            font-weight: 800;
            letter-spacing: -1.2px;
            line-height: 1.15;
            background: linear-gradient(135deg, #ffffff 30%, #cbd5e1 70%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            font-size: 16px;
            color: var(--text-muted);
            max-width: 580px;
            line-height: 1.6;
        }

        /* Platform Pills */
        .platforms-bar {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            margin-top: 4px;
        }

        .pill {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 12px;
            font-size: 12.5px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-glass);
            color: var(--text-muted);
            backdrop-filter: blur(8px);
            transition: all 0.25s ease;
        }

        .pill:hover {
            border-color: rgba(255, 255, 255, 0.2);
            color: var(--text-main);
            transform: translateY(-2px);
        }

        .pill-tiktok { color: #22d3ee; }
        .pill-fb { color: #60a5fa; }
        .pill-x { color: #f1f5f9; }
        .pill-yt { color: #f87171; }
        .pill-ig { color: #f472b6; }
        .pill-reddit { color: #fb923c; }

        /* Main Card */
        .glass-card {
            width: 100%;
            background: var(--bg-card);
            border: 1px solid var(--border-glass);
            border-radius: 24px;
            padding: 32px;
            backdrop-filter: blur(16px);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
            transition: border-color 0.3s ease;
        }

        .glass-card:focus-within {
            border-color: var(--border-glow);
        }

        /* Search & Input Form */
        .input-form {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .input-wrapper {
            position: relative;
            display: flex;
            align-items: center;
        }

        .url-input {
            width: 100%;
            height: 60px;
            padding: 0 130px 0 22px;
            background: rgba(10, 15, 26, 0.85);
            border: 1.5px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            color: var(--text-main);
            font-size: 16px;
            font-family: inherit;
            outline: none;
            transition: all 0.25s ease;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.4);
        }

        .url-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25), inset 0 2px 4px rgba(0,0,0,0.4);
        }

        .input-actions {
            position: absolute;
            right: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn-paste {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--border-glass);
            color: var(--text-muted);
            padding: 8px 14px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            font-family: inherit;
        }

        .btn-paste:hover {
            background: rgba(255, 255, 255, 0.15);
            color: var(--text-main);
        }

        .btn-submit {
            height: 56px;
            background: var(--primary-gradient);
            border: none;
            border-radius: 14px;
            color: white;
            font-size: 16px;
            font-weight: 700;
            font-family: 'Outfit', sans-serif;
            letter-spacing: 0.3px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            box-shadow: 0 10px 25px rgba(99, 102, 241, 0.4);
            transition: all 0.25s ease;
        }

        .btn-submit:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 14px 30px rgba(99, 102, 241, 0.55);
        }

        .btn-submit:disabled {
            opacity: 0.65;
            cursor: not-allowed;
            transform: none;
        }

        /* Detected badge under input */
        .detected-badge {
            display: none;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            font-weight: 600;
            color: var(--accent-cyan);
            margin-top: -6px;
        }

        /* Status / Error Messages */
        .alert-box {
            display: none;
            padding: 16px 20px;
            border-radius: 14px;
            font-size: 14.5px;
            line-height: 1.5;
            margin-top: 18px;
            animation: fadeIn 0.3s ease;
        }

        .alert-error {
            background: rgba(239, 68, 68, 0.12);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #fca5a5;
        }

        .alert-loading {
            background: rgba(99, 102, 241, 0.12);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #c7d2fe;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .spinner {
            width: 20px;
            height: 20px;
            border: 2.5px solid rgba(255, 255, 255, 0.2);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Video Preview Card */
        .preview-card {
            display: none;
            margin-top: 24px;
            padding: 24px;
            background: rgba(13, 19, 33, 0.9);
            border: 1px solid var(--border-glass);
            border-radius: 20px;
            gap: 24px;
            animation: fadeIn 0.35s ease;
        }

        @media (min-width: 680px) {
            .preview-card {
                display: none; /* toggle via JS flex */
                grid-template-columns: 240px 1fr;
            }
        }

        .thumb-wrapper {
            position: relative;
            border-radius: 14px;
            overflow: hidden;
            background: #000;
            aspect-ratio: 16/9;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
        }

        .thumb-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .thumb-badge {
            position: absolute;
            bottom: 8px;
            right: 8px;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(4px);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11.5px;
            font-weight: 700;
            color: white;
        }

        .platform-tag {
            position: absolute;
            top: 8px;
            left: 8px;
            background: rgba(99, 102, 241, 0.85);
            backdrop-filter: blur(4px);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            color: white;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .video-meta {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 16px;
        }

        .video-title {
            font-family: 'Outfit', sans-serif;
            font-size: 19px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.35;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .video-author {
            font-size: 14px;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 4px;
        }

        /* Formats Selection List */
        .formats-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: 8px;
        }

        .format-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            transition: all 0.2s ease;
        }

        .format-item:hover {
            background: rgba(255, 255, 255, 0.07);
            border-color: rgba(99, 102, 241, 0.3);
        }

        .format-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .format-badge {
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            background: rgba(99, 102, 241, 0.2);
            color: #a5b4fc;
            text-transform: uppercase;
        }

        .format-badge.audio {
            background: rgba(217, 70, 239, 0.2);
            color: #f0abfc;
        }

        .format-label {
            font-size: 14.5px;
            font-weight: 600;
            color: var(--text-main);
        }

        .format-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn-download-safe {
            padding: 8px 16px;
            background: #10b981;
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 13.5px;
            font-weight: 700;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }

        .btn-download-safe:hover {
            background: #059669;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
        }

        .btn-direct-link {
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-glass);
            border-radius: 10px;
            color: var(--text-muted);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: all 0.2s ease;
        }

        .btn-direct-link:hover {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.12);
        }

        /* Collapsible Settings / Guidance */
        .drawer-toggle {
            background: none;
            border: none;
            color: var(--text-dim);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 12px;
            transition: color 0.2s ease;
            font-family: inherit;
        }

        .drawer-toggle:hover {
            color: var(--text-muted);
        }

        .drawer-content {
            display: none;
            margin-top: 14px;
            padding: 18px 20px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 13px;
            color: var(--text-muted);
            line-height: 1.6;
        }

        .drawer-content input {
            width: 100%;
            margin-top: 8px;
            padding: 10px 14px;
            border-radius: 8px;
            background: rgba(10, 15, 26, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
            font-size: 13px;
            outline: none;
        }

        /* Toast notification */
        .toast {
            position: fixed;
            bottom: 24px;
            background: #1e293b;
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.15);
            padding: 12px 24px;
            border-radius: 100px;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: none;
            z-index: 100;
        }

        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }

        /* Footer */
        footer {
            margin-top: 24px;
            font-size: 13px;
            color: var(--text-dim);
            text-align: center;
        }

        footer a {
            color: var(--text-muted);
            text-decoration: none;
        }

        footer a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="ambient-glow glow-1"></div>
    <div class="ambient-glow glow-2"></div>
    <div class="ambient-glow glow-3"></div>

    <div class="wrapper">
        <header>
            <div class="brand-badge">
                <span class="pulse-dot"></span>
                Universal Video Downloader
            </div>
            <h1>Download Any Video in HD</h1>
            <p class="subtitle">Extract and save high-quality, watermark-free videos across popular social networks in seconds.</p>

            <div class="platforms-bar">
                <span class="pill pill-tiktok">✦ TikTok (HD No Watermark)</span>
                <span class="pill pill-fb">✦ Facebook (HD/SD)</span>
                <span class="pill pill-x">✦ X / Twitter</span>
                <span class="pill pill-yt">✦ YouTube</span>
                <span class="pill pill-ig">✦ Instagram</span>
                <span class="pill pill-reddit">✦ Reddit</span>
            </div>
        </header>

        <div class="glass-card">
            <form id="downloadForm" class="input-form">
                <div class="input-wrapper">
                    <input
                        id="urlInput"
                        type="url"
                        class="url-input"
                        placeholder="Paste video link here (YouTube, TikTok, Facebook, X, etc.)..."
                        required
                        autocomplete="off"
                        spellcheck="false"
                    />
                    <div class="input-actions">
                        <button type="button" id="pasteBtn" class="btn-paste">Paste</button>
                    </div>
                </div>

                <div id="detectedPlatform" class="detected-badge">
                    <span id="detectedIcon">⚡</span>
                    <span id="detectedText">Ready to extract</span>
                </div>

                <button type="submit" id="submitBtn" class="btn-submit">
                    <span>⚡ Fetch & Extract Video</span>
                </button>
            </form>

            <div id="alertBox" class="alert-box"></div>

            <div id="previewCard" class="preview-card">
                <div class="thumb-wrapper">
                    <img id="thumbImg" class="thumb-img" alt="Video thumbnail" src="" />
                    <span id="thumbDuration" class="thumb-badge">00:00</span>
                    <span id="thumbPlatform" class="platform-tag">PLATFORM</span>
                </div>
                <div class="video-meta">
                    <div>
                        <h2 id="videoTitle" class="video-title">Video Title</h2>
                        <div class="video-author">
                            <span>👤</span>
                            <span id="videoAuthor">Creator</span>
                        </div>
                    </div>

                    <div>
                        <div style="font-size: 13px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
                            Available Qualities:
                        </div>
                        <div id="formatsList" class="formats-list"></div>
                    </div>
                </div>
            </div>

            <button type="button" id="drawerToggle" class="drawer-toggle">
                <span>⚙</span> Advanced Settings & Proxy
            </button>
            <div id="drawerContent" class="drawer-content">
                <p><strong>Proxy Configuration (Optional):</strong> If you run into strict datacenter rate limits on YouTube or Instagram, provide a proxy (HTTP/HTTPS/SOCKS5):</p>
                <input id="proxyInput" type="text" placeholder="http://user:pass@proxy-ip:port" autocomplete="off" />
                <p style="margin-top: 10px; font-size: 12px; color: var(--text-dim);">
                    Tip: You can also permanently configure <code>PROXY_URL</code> or <code>YOUTUBE_COOKIES</code> in your Vercel Project Environment Variables.
                </p>
            </div>
        </div>

        <footer>
            Universal Media Downloader &bull; Powered by Vercel Serverless &bull; For personal, public media use only
        </footer>
    </div>

    <div id="toast" class="toast">Link copied to clipboard!</div>

    <script>
        const $ = (id) => document.getElementById(id);
        const form = $("downloadForm");
        const urlInput = $("urlInput");
        const pasteBtn = $("pasteBtn");
        const submitBtn = $("submitBtn");
        const alertBox = $("alertBox");
        const previewCard = $("previewCard");
        const detectedPlatform = $("detectedPlatform");
        const detectedText = $("detectedText");
        const proxyInput = $("proxyInput");
        const drawerToggle = $("drawerToggle");
        const drawerContent = $("drawerContent");
        const toast = $("toast");

        // Load saved proxy
        proxyInput.value = localStorage.getItem("omni-proxy") || "";
        proxyInput.addEventListener("input", () => {
            localStorage.setItem("omni-proxy", proxyInput.value.trim());
        });

        // Drawer toggle
        drawerToggle.addEventListener("click", () => {
            const isHidden = drawerContent.style.display === "none" || !drawerContent.style.display;
            drawerContent.style.display = isHidden ? "block" : "none";
        });

        // Show Toast
        function showToast(message) {
            toast.textContent = message;
            toast.classList.add("show");
            setTimeout(() => toast.classList.remove("show"), 2500);
        }

        // Platform detection in input
        function detectPlatform(url) {
            const lower = url.toLowerCase();
            if (lower.includes("tiktok.com")) return { name: "TikTok", color: "#22d3ee" };
            if (lower.includes("facebook.com") || lower.includes("fb.watch")) return { name: "Facebook", color: "#60a5fa" };
            if (lower.includes("twitter.com") || lower.includes("x.com")) return { name: "X / Twitter", color: "#f1f5f9" };
            if (lower.includes("youtube.com") || lower.includes("youtu.be")) return { name: "YouTube", color: "#f87171" };
            if (lower.includes("instagram.com")) return { name: "Instagram", color: "#f472b6" };
            if (lower.includes("reddit.com") || lower.includes("redd.it")) return { name: "Reddit", color: "#fb923c" };
            if (lower.includes("pinterest.com") || lower.includes("pin.it")) return { name: "Pinterest", color: "#e11d48" };
            return null;
        }

        urlInput.addEventListener("input", () => {
            const val = urlInput.value.trim();
            const detected = detectPlatform(val);
            if (detected) {
                detectedPlatform.style.display = "flex";
                detectedPlatform.style.color = detected.color;
                detectedText.textContent = detected.name + " link detected";
            } else {
                detectedPlatform.style.display = "none";
            }
        });

        // Clipboard Paste
        pasteBtn.addEventListener("click", async () => {
            try {
                const text = await navigator.clipboard.readText();
                urlInput.value = text;
                urlInput.dispatchEvent(new Event("input"));
                urlInput.focus();
            } catch (err) {
                urlInput.focus();
            }
        });

        function showAlert(msg, type = "error") {
            alertBox.style.display = "block";
            if (type === "loading") {
                alertBox.className = "alert-box alert-loading";
                alertBox.innerHTML = `<div class="spinner"></div><span>${msg}</span>`;
            } else {
                alertBox.className = "alert-box alert-error";
                alertBox.textContent = msg;
            }
        }

        function hideAlert() {
            alertBox.style.display = "none";
        }

        // Form Submit
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const url = urlInput.value.trim();
            if (!url) return;

            hideAlert();
            previewCard.style.display = "none";
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<div class="spinner" style="width:16px;height:16px;border-width:2px;"></div><span>Extracting Media Streams...</span>`;
            showAlert("Contacting media resolvers and fetching video streams...", "loading");

            try {
                const proxy = proxyInput.value.trim();
                const response = await fetch("/download", {
                    method: "POST",
                    headers: { 
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    body: JSON.stringify({ url: url, proxy: proxy || null })
                });

                const contentType = response.headers.get("content-type") || "";
                let data;
                if (contentType.includes("application/json")) {
                    data = await response.json();
                } else {
                    const text = await response.text();
                    const titleMatch = text.match(/<title>(.*?)<\/title>/i);
                    const serverMsg = titleMatch ? titleMatch[1] : (text.slice(0, 140) || "Server returned non-JSON response");
                    throw new Error(`Server returned error (${response.status}): ${serverMsg}`);
                }

                if (!response.ok) {
                    throw new Error(data.error || "Failed to process video.");
                }

                hideAlert();
                renderPreview(data);

            } catch (error) {
                showAlert(error.message || "Failed to fetch video information.");
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<span>⚡ Fetch & Extract Video</span>`;
            }
        });

        function renderPreview(data) {
            $("videoTitle").textContent = data.title || "Video";
            $("videoAuthor").textContent = data.author || data.platform_name || "Creator";
            $("thumbPlatform").textContent = data.platform_name || "VIDEO";
            $("thumbDuration").textContent = data.duration_text || "HD";

            if (data.thumbnail) {
                $("thumbImg").src = data.thumbnail;
                $("thumbImg").style.display = "block";
            } else {
                $("thumbImg").style.display = "none";
            }

            const formatsList = $("formatsList");
            formatsList.innerHTML = "";

            const formats = data.formats || [];

            if (formats.length === 0 && data.url) {
                formats.push({
                    id: "primary",
                    label: "Download Video (MP4)",
                    ext: "mp4",
                    quality: "HD",
                    url: data.url,
                    stream_url: `/stream?url=${encodeURIComponent(data.url)}&filename=${encodeURIComponent((data.title || "video") + ".mp4")}&platform=${data.platform || "generic"}`,
                    type: "video"
                });
            }

            formats.forEach(f => {
                const item = document.createElement("div");
                item.className = "format-item";

                const isAudio = f.type === "audio" || f.ext === "mp3" || f.ext === "m4a";
                const badgeClass = isAudio ? "format-badge audio" : "format-badge";

                item.innerHTML = `
                    <div class="format-info">
                        <span class="${badgeClass}">${f.quality || f.ext.toUpperCase()}</span>
                        <span class="format-label">${f.label || f.quality || "Standard"}</span>
                    </div>
                    <div class="format-actions">
                        <a href="${f.stream_url || f.url}" class="btn-download-safe" download>
                            <span>📥 Safe Download</span>
                        </a>
                        <a href="${f.url}" target="_blank" rel="noreferrer" class="btn-direct-link" title="Open direct media link">
                            <span>Direct</span>
                        </a>
                        <button type="button" class="btn-direct-link copy-btn" data-url="${f.stream_url ? window.location.origin + f.stream_url : f.url}" title="Copy download link">
                            <span>📋</span>
                        </button>
                    </div>
                `;
                formatsList.appendChild(item);
            });

            // Bind copy buttons
            document.querySelectorAll(".copy-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const copyUrl = btn.dataset.url;
                    navigator.clipboard.writeText(copyUrl);
                    showToast("Download link copied!");
                });
            });

            previewCard.style.display = "grid";
            previewCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    </script>
</body>
</html>
"""

def clean_filename(title: str, ext: str = "mp4") -> str:
    """Sanitizes filename for Content-Disposition header."""
    if not title:
        title = "video"
    # Remove control characters, quotes, and invalid filename characters
    cleaned = re.sub(r'[\/\\?%*:|"<>#\x00-\x1f]', '_', title).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    if len(cleaned) > 80:
        cleaned = cleaned[:80].strip()
    if not cleaned:
        cleaned = "video"
    ext = ext.lstrip(".").lower()
    return f"{cleaned}.{ext}"

def format_duration(seconds) -> str:
    if not seconds:
        return ""
    try:
        s = int(seconds)
        if s <= 0:
            return ""
        m, sec = divmod(s, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{sec:02d}"
        return f"{m:02d}:{sec:02d}"
    except Exception:
        return ""

def detect_platform(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return "generic"
        
    for prefix in ("www.", "m.", "music.", "v.", "mobile.", "web."):
        if host.startswith(prefix):
            host = host[len(prefix):]
            
    if any(d in host for d in ["tiktok.com"]):
        return "tiktok"
    if any(d in host for d in ["twitter.com", "x.com", "vxtwitter.com", "fxtwitter.com", "fixupx.com"]):
        return "twitter"
    if any(d in host for d in ["facebook.com", "fb.watch", "fb.com"]):
        return "facebook"
    if any(d in host for d in ["instagram.com", "instagr.am"]):
        return "instagram"
    if any(d in host for d in ["youtube.com", "youtu.be"]):
        return "youtube"
    if any(d in host for d in ["reddit.com", "redd.it"]):
        return "reddit"
    if any(d in host for d in ["pinterest.com", "pin.it"]):
        return "pinterest"
    if "threads.net" in host:
        return "threads"
    if "vimeo.com" in host:
        return "vimeo"
    return "generic"

def resolve_tiktok(url: str):
    """Dedicated TikTok extractor using TikWM API (watermark-free HD, no datacenter block)."""
    try:
        resp = requests.post(
            "https://www.tikwm.com/api/",
            data={"url": url, "hd": 1},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "application/json"
            },
            timeout=8
        )
        if resp.status_code == 200:
            res = resp.json()
            if res.get("code") == 0:
                d = res.get("data", {})
                title = d.get("title") or "TikTok Video"
                author = (d.get("author") or {}).get("nickname") or (d.get("author") or {}).get("unique_id") or "TikTok Creator"
                cover = d.get("cover") or d.get("origin_cover") or ""
                duration = d.get("duration") or 0
                
                formats = []
                hdplay = d.get("hdplay")
                play = d.get("play")
                music = d.get("music")
                
                if hdplay:
                    formats.append({
                        "id": "hd",
                        "label": "HD 1080p (No Watermark)",
                        "ext": "mp4",
                        "quality": "1080p",
                        "url": hdplay,
                        "stream_url": f"/stream?url={quote(hdplay)}&filename={quote(clean_filename(title, 'mp4'))}&platform=tiktok",
                        "type": "video"
                    })
                if play:
                    formats.append({
                        "id": "sd",
                        "label": "SD 720p (No Watermark)",
                        "ext": "mp4",
                        "quality": "720p",
                        "url": play,
                        "stream_url": f"/stream?url={quote(play)}&filename={quote(clean_filename(title, 'mp4'))}&platform=tiktok",
                        "type": "video"
                    })
                if music:
                    formats.append({
                        "id": "audio",
                        "label": "Audio Only (MP3)",
                        "ext": "mp3",
                        "quality": "Audio",
                        "url": music,
                        "stream_url": f"/stream?url={quote(music)}&filename={quote(clean_filename(title + ' - Audio', 'mp3'))}&platform=tiktok",
                        "type": "audio"
                    })
                
                if formats:
                    return {
                        "platform": "tiktok",
                        "platform_name": "TikTok",
                        "title": title,
                        "author": f"@{author}",
                        "thumbnail": cover,
                        "duration_text": format_duration(duration),
                        "formats": formats
                    }
    except Exception as e:
        print("TikWM API extraction error:", repr(e))

    # Fallback to yt-dlp
    return resolve_ytdlp(url, "tiktok")

def resolve_twitter(url: str):
    """Dedicated Twitter/X extractor using FxTwitter syndication API."""
    match = re.search(r"status/(\d+)", url)
    if match:
        tweet_id = match.group(1)
        try:
            api_url = f"https://api.fxtwitter.com/status/{tweet_id}"
            resp = requests.get(
                api_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                tweet = data.get("tweet", {})
                media = tweet.get("media", {})
                videos = media.get("videos") or ([media.get("video")] if media.get("video") else [])
                
                if videos:
                    v = videos[0]
                    title = tweet.get("text") or "X Video"
                    author = tweet.get("author", {}).get("name") or tweet.get("author", {}).get("screen_name") or "X User"
                    thumbnail = v.get("thumbnail_url") or ""
                    duration = v.get("duration") or 0
                    
                    formats = []
                    variants = v.get("variants") or []
                    if variants:
                        variants.sort(key=lambda x: x.get("bitrate", 0), reverse=True)
                        for idx, var in enumerate(variants):
                            v_url = var.get("url")
                            if not v_url or ".m3u8" in v_url:
                                continue
                            height = var.get("height") or 0
                            label = f"{height}p MP4" if height else f"Video Quality {idx+1}"
                            formats.append({
                                "id": f"x_{idx}",
                                "label": label,
                                "ext": "mp4",
                                "quality": f"{height}p" if height else "HD",
                                "url": v_url,
                                "stream_url": f"/stream?url={quote(v_url)}&filename={quote(clean_filename(title, 'mp4'))}&platform=twitter",
                                "type": "video"
                            })
                    
                    if not formats and v.get("url"):
                        formats.append({
                            "id": "direct",
                            "label": "HD Video (MP4)",
                            "ext": "mp4",
                            "quality": "HD",
                            "url": v.get("url"),
                            "stream_url": f"/stream?url={quote(v.get('url'))}&filename={quote(clean_filename(title, 'mp4'))}&platform=twitter",
                            "type": "video"
                        })
                        
                    if formats:
                        return {
                            "platform": "twitter",
                            "platform_name": "X / Twitter",
                            "title": title[:100],
                            "author": f"@{author}",
                            "thumbnail": thumbnail,
                            "duration_text": format_duration(duration),
                            "formats": formats
                        }
        except Exception as e:
            print("FxTwitter error:", repr(e))

    return resolve_ytdlp(url, "twitter")

def resolve_youtube(url: str, custom_proxy: str = None):
    """YouTube resolver with optimized player client parameters and Invidious fallback."""
    # 1. Try yt-dlp first
    try:
        result = resolve_ytdlp(url, "youtube", custom_proxy=custom_proxy)
        if result and result.get("formats"):
            return result
    except Exception as e:
        print("yt-dlp YouTube primary attempt failed:", repr(e))
        
    # 2. Try Invidious public instances fallback if datacenter IP is blocked
    m = re.search(r"(?:v=|\/embed\/|youtu\.be\/|\/v\/|\/shorts\/)([a-zA-Z0-9_-]{11})", url)
    if m:
        video_id = m.group(1)
        invidious_instances = [
            "https://inv.nadeko.net",
            "https://invidious.nerdvpn.de",
            "https://invidious.protokolla.fi",
            "https://yewtu.be"
        ]
        for instance in invidious_instances:
            try:
                api_endpoint = f"{instance}/api/v1/videos/{video_id}"
                resp = requests.get(api_endpoint, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    title = data.get("title") or "YouTube Video"
                    author = data.get("author") or "YouTube Channel"
                    thumbs = data.get("videoThumbnails") or []
                    thumbnail = thumbs[-1].get("url") if thumbs else ""
                    duration = data.get("lengthSeconds") or 0
                    
                    formats = []
                    for s in data.get("formatStreams", []):
                        s_url = s.get("url")
                        if not s_url:
                            continue
                        quality = s.get("qualityLabel") or s.get("resolution") or "Video"
                        container = s.get("container") or "mp4"
                        formats.append({
                            "id": f"inv_{quality}",
                            "label": f"{quality} ({container.upper()})",
                            "ext": container,
                            "quality": quality,
                            "url": s_url,
                            "stream_url": f"/stream?url={quote(s_url)}&filename={quote(clean_filename(title, container))}&platform=youtube",
                            "type": "video"
                        })
                    
                    for a in data.get("adaptiveFormats", []):
                        if (a.get("type") or "").startswith("audio/"):
                            a_url = a.get("url")
                            if a_url:
                                container = a.get("container") or "m4a"
                                formats.append({
                                    "id": "inv_audio",
                                    "label": f"Audio Only ({container.upper()})",
                                    "ext": container,
                                    "quality": "Audio",
                                    "url": a_url,
                                    "stream_url": f"/stream?url={quote(a_url)}&filename={quote(clean_filename(title + ' - Audio', container))}&platform=youtube",
                                    "type": "audio"
                                })
                                break
                                
                    if formats:
                        return {
                            "platform": "youtube",
                            "platform_name": "YouTube",
                            "title": title,
                            "author": author,
                            "thumbnail": thumbnail,
                            "duration_text": format_duration(duration),
                            "formats": formats
                        }
            except Exception as e:
                print(f"Invidious instance {instance} error:", repr(e))
                continue

    return resolve_ytdlp(url, "youtube", custom_proxy=custom_proxy)

def resolve_ytdlp(url: str, platform: str = "generic", custom_proxy: str = None):
    """Core yt-dlp extractor with multi-format ranking, headers, and proxy support."""
    proxy = custom_proxy or os.environ.get("PROXY_URL") or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "socket_timeout": 15,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
    }
    
    if proxy:
        opts["proxy"] = proxy.strip()
        
    # Cookie support from Vercel Environment Variables
    cookie_data = os.environ.get("COOKIES_DATA") or (
        os.environ.get("YOUTUBE_COOKIES") if platform == "youtube" else (
            os.environ.get("INSTAGRAM_COOKIES") if platform == "instagram" else None
        )
    )
    if cookie_data:
        cookie_path = "/tmp/cookies.txt"
        try:
            with open(cookie_path, "w", encoding="utf-8") as f:
                f.write(cookie_data)
            opts["cookiefile"] = cookie_path
        except Exception:
            pass
            
    if platform == "youtube":
        opts["extractor_args"] = {
            "youtube": {
                "player_client": ["mweb", "tv_embedded", "ios", "web"],
            }
        }
    elif platform == "tiktok":
        opts["extractor_args"] = {
            "tiktok": {
                "api_hostname": ["api16-normal-c-useast1a.tiktokv.com"],
            }
        }
        
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
    if not info:
        raise ValueError("Could not extract media metadata.")
        
    if "entries" in info and info["entries"]:
        for entry in info["entries"]:
            if entry:
                info = entry
                break
                
    title = info.get("title") or "Video"
    # Clean Facebook reaction prefixes from titles
    if platform == "facebook":
        title = re.sub(r'^\d+[KkMm]? views\s*·\s*[\d\.]+[KkMm]? reactions\s*｜\s*', '', title)
        
    author = info.get("uploader") or info.get("channel") or info.get("creator") or platform.capitalize()
    thumbnail = info.get("thumbnail") or ""
    duration = info.get("duration") or 0
    formats_raw = info.get("formats") or []
    
    parsed_formats = []
    progressive = []
    audio_formats = []
    
    for f in formats_raw:
        f_url = f.get("url")
        if not f_url or not isinstance(f_url, str):
            continue
        proto = (f.get("protocol") or "").lower()
        if "m3u8" in proto or "dash" in proto:
            continue
        clean_u = f_url.split("?")[0].lower()
        if clean_u.endswith(".m3u8") or clean_u.endswith(".mpd"):
            continue
            
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        has_video = vcodec and vcodec != "none"
        has_audio = acodec and acodec != "none"
        
        if has_video and has_audio:
            progressive.append(f)
        elif not has_video and has_audio:
            audio_formats.append(f)
            
    if progressive:
        progressive.sort(
            key=lambda x: (
                x.get("height") or 0,
                x.get("tbr") or x.get("vbr") or 0
            ),
            reverse=True
        )
        
        seen_res = set()
        for f in progressive:
            h = f.get("height") or 0
            res_key = f"{h}p" if h > 0 else "auto"
            if res_key in seen_res and res_key != "auto":
                continue
            seen_res.add(res_key)
            
            f_id = f.get("format_id") or "prog"
            ext = (f.get("ext") or "mp4").lower()
            label = f"HD {h}p" if h >= 720 else (f"{h}p" if h > 0 else "Best Available")
            
            if platform == "facebook":
                if "hd" in f_id.lower() or h >= 720:
                    label = "HD 720p / 1080p (High Quality)"
                else:
                    label = "SD (Standard Quality)"
                    
            f_url = f.get("url")
            parsed_formats.append({
                "id": f_id,
                "label": f"{label} ({ext.upper()})",
                "ext": ext,
                "quality": f"{h}p" if h > 0 else "HD",
                "url": f_url,
                "stream_url": f"/stream?url={quote(f_url)}&filename={quote(clean_filename(title, ext))}&platform={platform}",
                "type": "video"
            })
            
    root_url = info.get("url")
    if not parsed_formats and root_url:
        clean_r = root_url.split("?")[0].lower()
        if not (clean_r.endswith(".m3u8") or clean_r.endswith(".mpd")):
            parsed_formats.append({
                "id": "direct",
                "label": "Direct Video (MP4)",
                "ext": "mp4",
                "quality": "Direct",
                "url": root_url,
                "stream_url": f"/stream?url={quote(root_url)}&filename={quote(clean_filename(title, 'mp4'))}&platform={platform}",
                "type": "video"
            })
            
    if audio_formats:
        best_audio = max(audio_formats, key=lambda x: x.get("abr") or x.get("tbr") or 0)
        a_url = best_audio.get("url")
        ext = (best_audio.get("ext") or "m4a").lower()
        parsed_formats.append({
            "id": "audio",
            "label": f"Audio Only ({ext.upper()})",
            "ext": ext,
            "quality": "Audio",
            "url": a_url,
            "stream_url": f"/stream?url={quote(a_url)}&filename={quote(clean_filename(title + ' - Audio', ext))}&platform={platform}",
            "type": "audio"
        })
        
    if not parsed_formats:
        for f in reversed(formats_raw):
            f_u = f.get("url")
            if f_u:
                ext = (f.get("ext") or "mp4").lower()
                parsed_formats.append({
                    "id": "fallback",
                    "label": f"Download Stream ({ext.upper()})",
                    "ext": ext,
                    "quality": "Standard",
                    "url": f_u,
                    "stream_url": f"/stream?url={quote(f_u)}&filename={quote(clean_filename(title, ext))}&platform={platform}",
                    "type": "video"
                })
                break
                
    if not parsed_formats:
        raise ValueError("No downloadable progressive video or audio streams were found.")
        
    return {
        "platform": platform,
        "platform_name": platform.capitalize(),
        "title": title,
        "author": author,
        "thumbnail": thumbnail,
        "duration_text": format_duration(duration),
        "formats": parsed_formats
    }


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(500)
def handle_http_errors(e):
    # Ensure any request directed to API endpoints or expecting JSON receives JSON, not HTML
    wants_json = (
        request.path.startswith(("/download", "/api", "/info", "/stream"))
        or request.is_json
        or "application/json" in request.headers.get("Accept", "")
    )
    if wants_json:
        code = getattr(e, "code", 500)
        desc = getattr(e, "description", str(e))
        return jsonify({"error": desc, "status": code}), code
    return render_template_string(HTML)


@app.route("/", methods=["GET"])
@app.route("/api", methods=["GET"])
@app.route("/api/", methods=["GET"])
@app.route("/api/index", methods=["GET"])
@app.route("/api/index.py", methods=["GET"])
def home():
    # If a GET request to / or /api/index has ?url=..., process it as a download request
    if request.args.get("url"):
        return download()
    return render_template_string(HTML)


@app.route("/stream", methods=["GET"])
@app.route("/api/stream", methods=["GET"])
def stream_proxy():
    media_url = request.args.get("url")
    filename = request.args.get("filename") or "video.mp4"
    platform = request.args.get("platform") or "generic"
    custom_referer = request.args.get("referer")
    
    if not media_url:
        return jsonify({"error": "Missing media URL."}), 400
        
    media_url = unquote(media_url)
    filename = clean_filename(unquote(filename), filename.split(".")[-1] if "." in filename else "mp4")
    
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
    }
    
    # Custom headers to bypass CDN hotlink protection
    if custom_referer:
        headers["Referer"] = custom_referer
    elif platform == "tiktok":
        headers["Referer"] = "https://www.tiktok.com/"
    elif platform == "instagram":
        headers["Referer"] = "https://www.instagram.com/"
    elif platform == "twitter":
        headers["Referer"] = "https://twitter.com/"
    elif platform == "facebook":
        headers["Referer"] = "https://www.facebook.com/"
    elif platform == "youtube":
        headers["Referer"] = "https://www.youtube.com/"
        
    try:
        req = requests.get(media_url, headers=headers, stream=True, timeout=20)
        
        resp_headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": req.headers.get("Content-Type", "video/mp4"),
            "Cache-Control": "no-cache",
        }
        if "Content-Length" in req.headers:
            resp_headers["Content-Length"] = req.headers["Content-Length"]
        if "Accept-Ranges" in req.headers:
            resp_headers["Accept-Ranges"] = req.headers["Accept-Ranges"]
            
        def generate():
            for chunk in req.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk
                    
        return Response(stream_with_context(generate()), headers=resp_headers, status=req.status_code)
    except Exception as e:
        print("Stream proxy error:", repr(e))
        return jsonify({"error": f"Failed to stream media: {str(e)}"}), 502


@app.route("/download", methods=["GET", "POST"])
@app.route("/info", methods=["GET", "POST"])
@app.route("/api/download", methods=["GET", "POST"])
@app.route("/api/info", methods=["GET", "POST"])
@app.route("/api", methods=["POST"])
@app.route("/api/index", methods=["POST"])
@app.route("/api/index.py", methods=["POST"])
def download():
    data = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    elif request.form:
        data = request.form.to_dict()
        
    url = data.get("url") or request.args.get("url", "")
    url = url.strip()
    proxy = data.get("proxy") or request.args.get("proxy", "")
    proxy = proxy.strip() if proxy else None
    
    if not url:
        return jsonify({"error": "Please paste a video URL."}), 400
        
    platform = detect_platform(url)
    
    try:
        if platform == "tiktok":
            media_info = resolve_tiktok(url)
        elif platform == "twitter":
            media_info = resolve_twitter(url)
        elif platform == "youtube":
            media_info = resolve_youtube(url, custom_proxy=proxy)
        elif platform == "facebook":
            media_info = resolve_ytdlp(url, "facebook", custom_proxy=proxy)
        elif platform == "instagram":
            media_info = resolve_ytdlp(url, "instagram", custom_proxy=proxy)
        else:
            media_info = resolve_ytdlp(url, platform, custom_proxy=proxy)
            
        if not media_info or not media_info.get("formats"):
            return jsonify({
                "error": f"No downloadable video stream was found for this {platform.capitalize()} link. The video may be private, age-restricted, or removed."
            }), 404
            
        # Backward compatibility with existing UI
        media_info["url"] = media_info["formats"][0].get("url")
        media_info["success"] = True
        
        return jsonify(media_info)
        
    except yt_dlp.utils.DownloadError as e:
        err_msg = str(e)
        print("yt-dlp error:", err_msg)
        friendly = f"Could not access this {platform.capitalize()} video. It may be private, region-restricted, or login-protected."
        if any(token in err_msg.lower() for token in ["bot", "sign in", "confirm you're not", "429"]):
            friendly = (
                f"{platform.capitalize()} detected datacenter traffic from the cloud host. "
                "You can configure a residential proxy in Advanced Settings, or add PROXY_URL to your Vercel Environment Variables."
            )
        return jsonify({"error": friendly}), 400
        
    except Exception as e:
        print("Unexpected error:", repr(e))
        return jsonify({"error": f"Error extracting video: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )