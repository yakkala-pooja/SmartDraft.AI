module.exports = {
  devServer: {
    // Use setupMiddlewares instead of the deprecated options
    setupMiddlewares: (middlewares, devServer) => {
      if (!devServer) {
        throw new Error('webpack-dev-server is not defined');
      }
      return middlewares;
    }
  },
  webpack: {
    configure: (webpackConfig) => {
      // Remove deprecated options if they exist
      if (webpackConfig.devServer) {
        delete webpackConfig.devServer.onBeforeSetupMiddleware;
        delete webpackConfig.devServer.onAfterSetupMiddleware;
      }
      return webpackConfig;
    },
  },
}; 