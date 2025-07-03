# # utils/country_analyzer.py

# from collections import defaultdict
# from app import db

# # Import the CountrywiseData model from your main app
# from app import CountrywiseData

# def summarize_countries_db():
#     """
#     Summarizes all data in the CountrywiseData table:
#       - country_counts: total value per country (sum)
#       - monthly_by_country: {country: {'YYYY-MM': value, ...}}
#       - annual_avg: {country: average monthly value (across available months)}
#     """
#     records = CountrywiseData.query.all()

#     monthly_by_country = defaultdict(dict)
#     country_counts = defaultdict(float)
#     annual_avg = {}

#     for rec in records:
#         if rec.country and rec.year and rec.month:
#             ym_key = f"{rec.year:04d}-{rec.month:02d}"
#             # Sum value for each country, month
#             monthly_by_country[rec.country][ym_key] = monthly_by_country[rec.country].get(ym_key, 0) + (rec.value or 0)
#             country_counts[rec.country] += (rec.value or 0)

#     # Calculate average across available months for each country
#     for country, mmap in monthly_by_country.items():
#         if mmap:
#             avg = sum(mmap.values()) / len(mmap)
#             annual_avg[country] = round(avg, 2)

#     return {
#         'country_counts': dict(country_counts),
#         'monthly_by_country': dict(monthly_by_country),
#         'annual_avg': annual_avg
#     }
