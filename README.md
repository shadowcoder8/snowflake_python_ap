
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

    If you only want **YOU** to access the server (and keep it hidden from the entire internet), use **Tailscale**.

    1.  **Install Tailscale** on your VM: `curl -fsSL https://tailscale.com/install.sh | sh`
    2.  **Start it:** `sudo tailscale up` (Login with Google/Microsoft).
    3.  **Install Tailscale** on your Laptop/Phone and login.
    4.  Access via the **MagicDNS** name or Tailscale IP (e.g., `http://100.x.y.z`).
    5.  You do NOT need to open any firewall ports for this.

    ### 🌐 Option 4: No-IP (Free Domain Name)

    If you want a free custom name like `myapp.ddns.net` instead of an IP address:

    1.  **Log in to No-IP** and create a Hostname (A Record).
    2.  **Enter your VM's Public IP** address into No-IP.
    3.  Now you can visit `http://myapp.ddns.net`.
    4.  **Note:** This **DOES NOT** hide your IP address. Attackers can still see your server location.
    5.  **Note:** You must still open Port 80 in your firewall (see instructions above).

    ### ❓ Which option should I choose?

    | Option | Hides IP? | Requires Domain? | Best For... |
    | :--- | :--- | :--- | :--- |
    | **Direct IP** | ❌ No | No | Testing quickly. |
    | **No-IP** | ❌ No | No (Free Subdomain) | Easier to remember name (e.g. `myapp.ddns.net`). |
    | **Tailscale** | ✅ **YES** | No | **Private Access.** Only YOU can access it (VPN). |




