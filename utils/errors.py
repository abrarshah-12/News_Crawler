class ScraperError(Exception):
    """Base class for scraper exceptions."""
    pass

class FirecrawlError(ScraperError):
    """Exception raised when Firecrawl fails."""
    pass


class GeminiError(Exception):
    """Exception raised when Gemini API fails."""
    pass

class ProcessingError(Exception):
    """Base class for data processing exceptions."""
    pass


class FileProcessingError(ProcessingError):
    """Exception raised when processing files fails."""
    pass