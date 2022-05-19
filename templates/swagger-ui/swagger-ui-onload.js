window.onload = function() {
    const ui = SwaggerUIBundle({
        url: "static/swagger.json",
        dom_id: "#swagger-ui",
        validatorUrl: null,
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout"
      });
    // End Swagger UI call region

    window.ui = ui;
};

