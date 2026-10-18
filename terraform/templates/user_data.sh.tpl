#!/bin/bash
dnf update -y
dnf install -y nginx
systemctl start nginx
systemctl enable nginx

TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone)

cat <<HTML > /usr/share/nginx/html/index.html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Service Node Status</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #ffffff;
      color: #111827;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 24px;
    }
    .container {
      width: 100%;
      max-width: 460px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid #e5e7eb;
    }
    h1 {
      font-size: 20px;
      font-weight: 600;
      color: #111827;
      letter-spacing: -0.3px;
    }
    .status {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      font-weight: 600;
      color: #16a34a;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .status-dot {
      width: 7px;
      height: 7px;
      background: #16a34a;
      border-radius: 50%;
    }
    .grid {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 14px;
    }
    .label {
      color: #6b7280;
    }
    .val {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
      font-weight: 500;
      color: #111827;
    }
    .meta {
      margin-top: 28px;
      padding-top: 16px;
      border-top: 1px solid #e5e7eb;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      color: #9ca3af;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Service Node Status</h1>
      <div class="status">
        <span class="status-dot"></span>
        <span>HEALTHY</span>
      </div>
    </div>
    <div class="grid">
      <div class="row">
        <span class="label">Availability Zone</span>
        <span class="val">$AZ</span>
      </div>
      <div class="row">
        <span class="label">Node Identifier</span>
        <span class="val">${node_name}</span>
      </div>
      <div class="row">
        <span class="label">Instance ID</span>
        <span class="val">$INSTANCE_ID</span>
      </div>
      <div class="row">
        <span class="label">Routing Path</span>
        <span class="val">ALB Target Group</span>
      </div>
      <div class="row">
        <span class="label">HTTP Response</span>
        <span class="val">200 OK</span>
      </div>
    </div>
    <div class="meta">sec-pipeline-cluster</div>
  </div>
</body>
</html>
HTML
