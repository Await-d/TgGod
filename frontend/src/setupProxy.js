const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8001',
      changeOrigin: true,
      onError: function(err, req, res) {
        console.error('Proxy error:', err);
        res.status(500).send('Proxy error: ' + err.message);
      },
      onProxyReq: function(proxyReq, req, res) {
        console.log('Proxying request:', req.method, req.url, 'to http://localhost:8001');
      }
    })
  );

  app.use(
    '/ws',
    createProxyMiddleware({
      target: 'ws://localhost:8001',
      changeOrigin: true,
      ws: true,
      onError: function(err, req, res) {
        console.error('WebSocket proxy error:', err);
      }
    })
  );
};