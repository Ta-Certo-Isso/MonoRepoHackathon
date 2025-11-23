Deploy a FastAPI App
FastAPI is a modern, high-performance web framework for building APIs with Python 3.7+ based on standard Python type hints.

Here's how to deploy a basic FastAPI app on Render.

Create your own repository using the render-examples/fastapi template on GitHub.
Alternatively, you can clone the repo and push your clone to GitLab or Bitbucket.
Create a new Web Service on Render, and give Render permission to access your new repo.
Provide the following values during service creation:
Setting	Value
Language	Python 3
Build Command	pip install -r requirements.txt
Start Command	uvicorn main:app --host 0.0.0.0 --port $PORT
That's it! Your web service will be live at its onrender.com URL as soon as the deploy finishes.

See Specifying a Python Version if you need to customize the version of Python used for your app.

Docker on Render
Build from a Dockerfile or pull from a container registry.
Render fully supports Docker-based deploys. Your services can:

Pull and run a prebuilt image from a registry such as Docker Hub, or
Build their own image at deploy time based on the Dockerfile in your project repo.
Render also provides native language runtimes that don't require Docker.

If you aren't sure whether to use Docker or a native runtime for your service, see this section.

Docker deployment methods
Pulling from a container registry
To pull a prebuilt Docker image from a container registry and run it on Render, see this article.

Building from a Dockerfile
Render can build your service's Docker image based on the Dockerfile in your project repo. To enable this, apply the following settings in the Render Dashboard during service creation:

Set the Language field to Docker (even if your application uses a language listed in the dropdown):

Selecting the Docker language runtime during service creation

If your Dockerfile is not in your repo's root directory, specify its path (e.g., my-subdirectory/Dockerfile) in the Dockerfile Path field:

Specifying the Dockerfile path during service creation

If your build process will need to pull any private image dependencies from a container registry (such as Docker Hub), provide a corresponding credential in the Registry Credential field under Advanced:

Adding a registry credential during service creation

Learn more about adding registry credentials.

If Render should run a custom command to start your service instead of using the CMD instruction in your Dockerfile (this is uncommon), specify it in the Docker Command field under Advanced:

Specifying a custom command during service creation

To run multiple commands, provide them to /bin/bash -c.

For example, here's a Docker Command for a Django service that runs database migrations and then starts the web server:

Copy to clipboard
/bin/bash -c python manage.py migrate && gunicorn myapp.wsgi:application --bind 0.0.0.0:10000
Note that you can't customize the command that Render uses to build your image.

Specify the remainder of your service's configuration as appropriate for your project and click the Deploy button.

You're all set! Every time a deploy is triggered for your service, Render uses BuildKit to generate an updated image based on your repo's Dockerfile. Render stores your images in a private, secure container registry.

Your Docker-based services support zero-downtime deploys, just like services that use a native language runtime.

Docker or native runtime?
Render provides native language runtimes for Node.js, Python, Ruby, Go, Rust, and Elixir. If your project uses one of these languages and you don't already use Docker, it's usually faster to get started with a native runtime. See Your First Render Deploy.

You should use Docker for your service in the following cases:

Your project already uses Docker.
Your project uses a language that Render doesn't support natively, such as PHP or a JVM-based language (such as Java, Kotlin, or Scala).
Your project requires OS-level packages that aren't included in Render's native runtimes.
With Docker, you have complete control over your base operating system and installed packages.
You need guaranteed reproducible builds.
Native runtimes receive regular updates to improve functionality, security, and performance. Although we aim to provide full backward compatibility, using a Dockerfile is the best way to ensure that your production runtime always matches local builds.
Most platform capabilities are supported identically for Docker-based services and native runtime services, including:

Zero-downtime deploys
Setting a pre-deploy command to run database migrations and other tasks before each deploy
Private networking
Support for persistent disk storage
Custom domains
Automatic Brotli and gzip compression
Infrastructure as code support with Render Blueprints
Docker-specific features
Environment variable translation
If you set environment variables for a Docker-based service, Render automatically translates those values to Docker build arguments that are available during your image's build process. These values are also available to your service at runtime as standard environment variables.

In your Dockerfile, do not reference any build arguments that contain sensitive values (such as passwords or API keys).

Otherwise, those sensitive values might be included in your generated image, which introduces a security risk. If you need to reference sensitive values during a build, instead add a secret file to your build context. For details, see Using Secrets with Docker.

Image builds
Render supports parallelized multi-stage builds.
Render omits files and directories from your build context based on your .dockerignore file.
Image caching
Render caches all intermediate build layers in your Dockerfile, which significantly speeds up subsequent builds. To further optimize your images and improve build times, follow these instructions from Docker.

Render also maintains a cache of public images pulled from container registries. Because of this, pulling an image with a mutable tag (e.g., latest) might result in a build that uses a cached, less recent version of the image. To ensure that you don't use a cached public image, do one of the following:

Reference an immutable tag when you deploy (e.g., a specific version like v1.2.3)
Add a credential to your image. For details, see Credentials for private images.
Popular public images
See quickstarts for deploying popular open-source applications using their official Docker images:

Infrastructure components

ClickHouse
Elasticsearch
MongoDB
MySQL
n8n
Temporal
Blogging and content management

Ghost
Wordpress
Analytics and business intelligence

Ackee
Fathom Analytics
GoatCounter
Matomo
Metabase
Open Web Analytics
Redash
Shynet
Communication and collaboration

Forem
Mattermost
Zulip

Build Pipeline
Render's build pipeline handles the tasks that occur before a new deploy of your service goes live. Depending on your service, these tasks might include:

Running your build command (yarn, pip install, etc.)
Running your pre-deploy command (for database migrations, asset uploads, etc.)
Building an image from a Dockerfile
All pipeline tasks consume pipeline minutes. Each workspace receives an included monthly allotment of pipeline minutes, and you can purchase additional minutes as needed.

Professional workspaces and higher can enable the Performance pipeline tier to run pipeline tasks on larger compute instances.

View your current month's pipeline usage from your Billing page.

Pipeline tiers
Professional workspaces and higher can choose between two pipeline tiers: Starter and Performance.

Hobby workspaces always use the Starter tier.

Tier	Specs	Description
Starter (default)	2 CPU
8 GB RAM	
For Hobby workspaces, includes 500 pipeline minutes per month.

For Professional workspaces and higher, includes 500 minutes per member per month (shared among all members).

Recommended unless your pipeline tasks require additional memory or CPU.

Performance	16 CPU
64 GB RAM	
Available only for Professional workspaces and higher. Runs tasks on compute instances with significantly higher memory and CPU.

Does not provide an included monthly allotment of pipeline minutes. Performance pipeline minutes are billed at a higher rate than Starter minutes.

Use this tier if your pipeline tasks require memory or CPU beyond what's provided by the Starter tier.

Specs and pricing details for each tier are available from your Workspace Settings page in the Render Dashboard.

Setting your pipeline tier
Your pipeline tier is a workspace-wide setting. Every pipeline task across your workspace uses the same tier.

In the Render Dashboard, go to your Workspace Settings page.
In the Build Pipeline section, select a pipeline tier.
Confirm your selection in the dialog that appears.
Pipeline minutes
While they're running, your builds and other pipeline tasks consume pipeline minutes. You can view your current month's usage from your Billing page.

Pipeline minutes are specific to their associated tier. You can't use Starter minutes with the Performance tier or vice versa.

Included minutes
Hobby workspaces receive 500 Starter-tier pipeline minutes per month. Professional workspaces and higher receive 500 Starter-tier minutes per member per month (shared among all members).

The Performance tier does not provide an included monthly allotment of pipeline minutes.

Running out of minutes
If you run out of pipeline minutes during a given month, you automatically purchase an additional allotment of minutes for your current tier, unless:

You've reached your monthly spend limit, or
You haven't added a payment method.
In the above cases, Render stops running pipeline tasks (including service builds!) for the remainder of the current month. You can reenable pipeline tasks by raising your spend limit (and adding a payment method if you haven't).

Setting a spend limit
You can set a maximum amount to spend on pipeline minutes each month. As long as you're under your limit for a given month, you automatically purchase an additional allotment of minutes whenever you run out.

In the Render Dashboard, go to your Workspace Settings page.
In the Build Pipeline section, click Set spend limit (or Edit if you're editing an existing limit).
Specify a new limit in the dialog that appears.
Build limits
Render cancels a build if any of the following occurs:
Memory usage exceeds the limit for your pipeline tier.
Disk space usage exceeds 16 GB.
Your build command fails or times out (after 120 minutes).
Your pre-deploy command fails or times out (after 30 minutes).
Each Render service can have only one active build at a time.
Whenever a new build is initiated, Render cancels any in-progress build for the same service.
Builds don't have access to your running service instance's resources (such as memory or disk).
This is because pipeline tasks run on completely separate compute.

Your First Render Deploy
Run your web app in minutes.
Welcome! Let's get up and running on Render.

This tutorial uses free Render resources—no payment required. All you need is a GitHub repo with the web app you want to deploy (GitLab and Bitbucket work too).

Want to deploy an example app using a particular language or framework?

Check out our quickstarts.

1. Sign up
Signing up is fast and free:

Sign up for Render

2. Choose a service type
To deploy to Render, you create a service that pulls, builds, and runs your code.

Launch the Render Dashboard.

In the top-right corner, open the + New dropdown:

The "New" dropdown in the Render dashboard

Here you select a service type.

For this tutorial, choose Web Service or Static Site:

Service type	Description	Common frameworks
Web Service

Choose this if your web app runs any server-side code. The app also needs to listen for HTTP requests on a port.

Full-stack web apps, API servers, and mobile backends are all web services.

Express, Next.js, Fastify, Django, FastAPI, Flask, Rails, Phoenix

Static Site

Choose this if your web app consists entirely of static content (mostly HTML/CSS/JS).

Blogs, portfolios, and documentation sets are often (but not always) static sites.

Create React App, Vue.js, Hugo, Docusaurus, Next.js static exports

You can deploy either of these service types for free on Render.

Free web services "spin down" after 15 minutes of inactivity.

They spin back up when they next receive incoming traffic. Learn more about free instance limitations.

3. Link your repo
After you select a service type, the service creation form appears.

First, connect your GitHub/GitLab/Bitbucket account to Render:

Options for connecting your Git provider to Render

After you connect, the form shows a list of all the repos you have access to:

List of available repos to use for a new service

Select the repo that contains your web app and click Connect.

The rest of the creation form appears.

4. Configure deployment
Complete the service creation form to define how Render will build and run your app.

Click the tab for your service type to view important field details:

Web Service
Static Site
Important web service fields
Field	Description
Branch

Your service only deploys commits on the branch you specify, such as main. Render can automatically redeploy your app whenever you push changes to this branch.

Root Directory

Deploying from a monorepo? Specify the subdirectory that represents your application root. Your build and start commands will run from this directory.

Language

If your app's programming language isn't listed in this dropdown, you can still deploy using the Docker runtime if you build your app from a Dockerfile.

Build Command

This is the command that Render will use to build your app from source.

Common examples include:

Node.js
Python
Ruby
Copy to clipboard
npm install
You can also use yarn or bun.

This usually resembles the command you run locally to install dependencies and perform any necessary compilation.

Start Command

This is the command that Render will use to start your app.

Common examples include:

Node.js
Python
Ruby
Copy to clipboard
npm start
You can also use yarn or bun.

For some frameworks, this might differ from the command you run locally to start your app. For example, a Flask app might use flask run locally but gunicorn for production.

Instance Type

This determines your service's RAM and CPU, along with its cost.

Choose the Free instance type to deploy for free:

Selecting the Free instance type

Environment Variables

These will be available to your service at both build time and runtime.

If you forget any, you can always add them later and redeploy.

When you're done, click the Deploy button at the bottom of the form. Render kicks off your first deploy.

5. Monitor your deploy
Render automatically opens a log explorer that shows your deploy's progress:

Logs for a service deploy

Follow along as the deploy proceeds through your build and start commands.

If the deploy completes successfully, the deploy's status updates to Live and you'll see log lines like these:

Copy to clipboard
# Web service
==> Deploying...
==> Running 'npm start' # (or your start command)
==> Your service is live 🎉

# Static site
==> Uploading build...
==> Your site is live 🎉
If the deploy fails, the deploy's status updates to Failed. Review the log feed to help identify the issue.

Also see Troubleshooting Your Deploy for common solutions.
After you identify the issue, push a new commit to your linked branch. Render will automatically start a new deploy.
6. Open your app
After your app deploys successfully, you're ready to view it live.

Every Render web service and static site receives a unique onrender.com URL. Find this URL on your service's page in the Render Dashboard:

A service's onrender.com URL

Click the URL to open it in your browser. Your service will serve the content for its root path.

Congratulations! You've deployed your first app on Render 🎉

When you're ready, check out recommended next steps.

Next steps
Connect a datastore
Render provides fully managed Postgres and Key Value instances for your data needs. Both provide a Free instance type to help you get started.

Free Render Postgres databases expire 30 days after creation.

You can upgrade to a paid instance at any time to keep your data. Learn more about free instance limitations.

Learn how to create datastores and connect them to your app:

Render Postgres databases
Render Key Value instances
Paid services can also attach a disk for persistence of local filesystem data (by default, local filesystem changes are lost with each deploy).

Install the Render CLI
The Render CLI helps you manage your Render services right from your terminal. Trigger deploys, view logs, initiate psql sessions, and more.

Get started with the Render CLI.

Add a custom domain
Each Render web service and static site receives its own onrender.com URL. You can also add your own custom domains to these service types. Learn how.

Learn about operational controls
Deploying your app is just the beginning. Check out a few of the ways you can manage and monitor your running services on Render:

Scaling your instance count
Analyzing service metrics
Rolling back a deploy
Enabling maintenance mode
Note that some of these capabilities require running your service on a paid instance type.

Explore other service types
In addition to supporting web services and static sites, Render offers a variety of other service types to support any use case:

Service type	Description
Private services	Run servers that aren't reachable from the public internet.
Background Workers	Offload long-running and computationally expensive tasks from your web servers.
Cron Jobs	Run periodic tasks on a schedule you define.
Note that free instances are not available for these service types.

Use this flowchart to help determine which service type is right for your use case:

Nope.

Yes!

No, my app includes
server-side logic.

Yes!

No, any traffic
is outgoing.

Yes!

Continuously.

Periodically.

Will your app receive traffic from the public internet (browsers, mobile apps, etc.)?

Does your app consist of statically served files (HTML, CSS, JS, etc.)?

Will your app receive private network traffic from your other Render services?

Will your app run continuously, or periodically on a schedule?

Create a
Static site

Create a
Web service

Create a
Background
worker

Create a
Cron job

Create a
Private service

-----

## Configuração recomendada para o MVP (whatsappchatbot)

- Root Directory: `Nichols`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn Nichols.main:app --host 0.0.0.0 --port $PORT`
- Healthcheck: `GET /health`

### Variáveis de ambiente essenciais

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (ex: `gpt-4o-mini`)
- `OPENAI_TTS_MODEL` (ex: `tts-1`)
- `OPENAI_TTS_VOICE` (ex: `alloy`)
- `OPENAI_EMBEDDINGS_MODEL` (ex: `text-embedding-3-small`)
- `EVOLUTION_BASE_URL` (ex: `https://<seu-host-evo>`)
- `EVOLUTION_API_KEY`
- `EVOLUTION_INSTANCE`
- `DATA_DIR` (ex: `data`) — diretório com `.txt` (primeira linha = título) para o RAG
- `HISTORY_DB` (ex: `data/history.db`)
- `WEBHOOK_TOKEN` (opcional, para validar o header `x-webhook-token`)

### Lembretes

- Aponte o webhook do Evolution API para `POST /webhook/evolution`.
- Para testar sem WhatsApp, use `POST /api/ask` com JSON `{"question": "...", "session_id": "<fone>"}`.
