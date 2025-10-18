FROM nginx:alpine

# 複製 Nginx 設定檔
COPY nginx.conf /etc/nginx/nginx.conf

# 暴露端口
EXPOSE 8897

# 啟動 Nginx
CMD ["nginx", "-g", "daemon off;"]
