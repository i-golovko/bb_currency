# Backbase assignment

Table of Contents

## About the Project

This is a sample application for a technical assignment.
It implements following features:
* Currency converter based on (almost) real time exchange rates.
* Chart representing change of exchange rates of currencies (USD, GBP, CHF) based on EUR.
* API methods to perform following operations:
  * Convert some amount of base currency to target currency
  * Git list of exchange rates for given currency for a given period of time
  * Get time series list of TWRR for a given amount of base currency invested into target currency
* Exchange rates are either fetched from remote currency rates providers, 
  which can be configured through admin site, or generated in a JSON file based on real rates.
* Once a day a background Celery task fetches exchange rates for the previous day.
* Every 10 minutes a background Celery task generates new mocked latest rates in JSON file.


# Getting Started

## Installation
```
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py loaddata fixtures/seed_rates.json
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --no-input
```


# Usage

## To access API methods
Navigate to `127.0.0.1:8000/docs/`

## To access admin site, providers configuration, currency converter and chart view
Navigate to `127.0.0.1:8000/admin/`

