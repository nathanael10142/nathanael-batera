class ApiConfig {
  // URL de base du backend déployé sur Render.
  // L'ancienne URL pour le développement local était "http://10.0.2.2:8000"
  static const String _baseUrl = "https://unigom-by-nathanael-batera.onrender.com";

  // Le préfixe de l'API défini dans votre backend FastAPI
  static const String _apiPrefix = "/api/v1";

  /// URL de base complète pour l'API
  /// Exemple : http://10.0.2.2:8000/api/v1
  static const String apiUrl = _baseUrl + _apiPrefix;
}