# Laila Self Guide Chat - Webflow Integration Guide

This guide will help you set up the Laila Self Guide Chat in your Webflow members-only area.

## Prerequisites

- A Webflow account with a site that has membership capabilities enabled
- A Vercel account for hosting the chat API
- An OpenAI account with API access and an Assistant created

## Step 1: Deploy the Chat API to Vercel

1. Fork or clone the API repository to your own GitHub account
2. Connect your GitHub repository to Vercel
3. Configure the following environment variables in Vercel:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `OPENAI_ASSISTANT_ID`: The ID of your Laila Self Guide Assistant

4. Deploy the API to Vercel
5. Once deployed, note your Vercel deployment URL (e.g., `https://laila-self-api.vercel.app`)

## Step 2: Add the Chat Interface to Webflow

### Option 1: Using Embed Code

1. In your Webflow editor, navigate to the page where you want to add the chat interface
2. Add an Embed element to the page
3. Copy the contents of the `webflow-chat.html` file
4. Paste it into the Embed element's code field
5. **Important**: Update the `API_URL` variable in the JavaScript to your Vercel deployment URL:
   ```javascript
   const API_URL = 'https://your-vercel-deployment-url.vercel.app';
   ```
6. Save and publish your Webflow site

### Option 2: Using Custom Code in the Header/Footer

1. In your Webflow project settings, navigate to Custom Code
2. Copy the contents of the `webflow-chat.html` file
3. Paste it into the Footer Code section
4. **Important**: Update the `API_URL` variable in the JavaScript to your Vercel deployment URL
5. Add a div with the id `laila-chat-container` where you want the chat to appear:
   ```html
   <div id="laila-chat-container"></div>
   ```
6. Save and publish your Webflow site

## Step 3: Configure Webflow Membership Access

1. In Webflow, go to your site's Membership settings
2. Create a new membership plan or use an existing one
3. Set the page with the chat interface to be accessible only to logged-in members
4. Publish your changes

## Step 4: CORS Configuration (Optional)

If you encounter CORS issues:

1. Edit the `main.py` file in your API repository
2. Update the CORS middleware configuration to include your Webflow domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.webflow.io",  # Webflow preview domains
        "https://*.webflow.com", # Webflow editor
        "https://your-webflow-site.com",  # Your custom domain
        os.getenv("PRODUCTION_DOMAIN", "http://localhost:3000")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600  # Cache preflight requests for 1 hour
)
```

3. Redeploy your API to Vercel

## Step 5: Testing

1. Log in to your Webflow site as a member
2. Navigate to the page with the chat interface
3. Try sending a message like "Tell me about Haven and my Laila Self"
4. Verify that you receive a response from the assistant
5. Test the "View Chat History" feature to ensure it's working correctly

## User Identification

The chat interface automatically generates a unique user ID for each visitor and stores it in their browser's localStorage. This allows the system to maintain unique conversations for each user.

If you want to use Webflow's member ID instead:

1. Get the Webflow member ID from the client-side:
```javascript
// Replace this code in webflow-chat.html
let userId = localStorage.getItem('lailaUserId');
if (!userId) {
    userId = 'user_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('lailaUserId', userId);
}

// With this code that uses Webflow member ID
let userId = Webflow.memberstack?.member?.id || localStorage.getItem('lailaUserId');
if (!userId) {
    userId = 'user_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('lailaUserId', userId);
}
```

## Customization

To customize the appearance of the chat interface:

1. Edit the CSS styles in the `<style>` section of the HTML
2. Adjust colors, sizes, and layout to match your Webflow site's design
3. You can add custom fonts, images, or branding elements as needed

## Troubleshooting

- **API Connection Issues**: Ensure your Vercel deployment is running and the API_URL is correct
- **CORS Errors**: Add your Webflow domain to the allowed origins in the API's CORS settings
- **Chat Not Loading**: Check browser console for JavaScript errors
- **Rate Limiting**: If you hit OpenAI rate limits, adjust the rate_limit_delay in assistant_manager.py

## Support

If you encounter any issues with the integration, please contact support or file an issue in the repository. 