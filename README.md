
## 🚀 Deployment (Oracle Linux / RHEL)

To deploy this application on an Oracle Linux VM (or any RHEL-based system):

1.  **Copy the deployment script** or clone the repository to your VM.
2.  **Make the script executable:**
    ```bash
    chmod +x deployment/deploy.sh
    ```
3.  **Run the script:**
    ```bash
    ./deployment/deploy.sh
    ```
    This script will automatically:
    *   Update system packages.
    *   Install Git, Docker, and Docker Compose.
    *   Clone the repository.
    *   Set up the environment.
    *   Start the application using `docker-compose.prod.yml`.

4.  **Access the API:**
    
    The application is served via Nginx on **Port 80**.
    
    *   **Public URL:** `http://<YOUR_SERVER_PUBLIC_IP>/`
    *   **API Documentation:** `http://<YOUR_SERVER_PUBLIC_IP>/docs`

    > **Note:** Direct access to port 8000 is blocked for security. You must go through Nginx (Port 80).

    ### 🛡️ Firewall Setup

    If you cannot access the API, you likely need to open Port 80 in the firewall.

    **Option A: For Oracle Linux / RHEL / CentOS (using firewalld)**
    ```bash
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --permanent --add-service=https
    sudo firewall-cmd --reload
    ```
    *If `firewall-cmd` is not found, try Option B.*

    **Option B: For Ubuntu / Debian (using UFW)**
    ```bash
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw reload
    ```

    **Option C: Oracle Cloud (OCI) Console Steps**
    1.  Log in to **Oracle Cloud Console**.
    2.  Navigate to **Compute** -> **Instances** and click your instance.
    3.  Click the link under **Subnet** (in the "Primary VNIC" section).
    4.  Click the **Security List** name (e.g., "Default Security List...").
    5.  Click **Add Ingress Rules**.
    6.  Enter the following:
        *   **Source CIDR:** `0.0.0.0/0`
        *   **IP Protocol:** `TCP`
        *   **Destination Port Range:** `80` (Add another rule for `443` if using HTTPS)
    7.  Click **Add Ingress Rules**.

    ### 🔒 Hiding Your Server IP (Advanced)
    
    If you do not want to expose your VM's Public IP directly, you can use **Cloudflare Tunnel** (Zero Trust). This requires no open ports (you can even close Port 80/443).

    1.  **Sign up for Cloudflare** and add your domain.
    2.  Go to **Zero Trust > Networks > Tunnels**.
    3.  Create a tunnel and choose **Debian/RedHat** (based on your OS).
    4.  Run the provided installation command on your VM.
    5.  In the tunnel configuration, map your domain (e.g., `api.yourdomain.com`) to the local Docker service:
        *   **Service:** `HTTP`
        *   **URL:** `localhost:80` (or `snowflake_nginx:80` if running cloudflared in docker)
    
    This way, users only see Cloudflare's IP, and your origin server remains hidden.
