FROM nginx:alpine

# Copy the web assets to Nginx html directory
COPY web /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
