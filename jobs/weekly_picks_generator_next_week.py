"""
Temporary script to run weekly picks generator for NEXT WEEK (2025-11-03)
For Loop 3 Iteration 2 testing
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jobs.weekly_picks_generator import WeeklyPicksGenerator, GeneratorConfig, logger

def main():
    """Run generator for next week (2025-11-03)"""
    import time
    start_time = time.time()
    
    # Calculate next Monday (Nov 3, 2025)
    today = datetime(2025, 10, 30)  # Current date
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    next_week_str = next_monday.strftime("%Y-%m-%d")
    
    logger.info(f"🎯 LOOP 3 ITERATION 2: Generating picks for NEXT WEEK: {next_week_str}")
    
    # Ensure output directory exists
    GeneratorConfig.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create generator and override week
    generator = WeeklyPicksGenerator()
    
    # Override the _get_week_start_date method to return next week
    original_method = generator._get_week_start_date
    generator._get_week_start_date = lambda: next_week_str
    
    # Run generator
    success = generator.run()
    
    elapsed = time.time() - start_time
    
    # Check performance target
    if elapsed > GeneratorConfig.MAX_EXECUTION_TIME:
        logger.warning(f"⚠️ Execution time ({elapsed:.2f}s) exceeded target ({GeneratorConfig.MAX_EXECUTION_TIME}s)")
    else:
        logger.info(f"✅ Execution completed within target time ({elapsed:.2f}s < {GeneratorConfig.MAX_EXECUTION_TIME}s)")
    
    logger.info(f"✅ Generated picks for week: {next_week_str}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
