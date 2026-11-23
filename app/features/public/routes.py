import logging

from flask import make_response, render_template, request

from app.features.dataset.services import DataSetService
from app.features.featuremodel.services import FeatureModelService
from app.features.public import public_bp
from app.features.statistics.services import StatisticsService

logger = logging.getLogger(__name__)


@public_bp.route("/")
def index():
    logger.info("Access index")
    dataset_service = DataSetService()
    feature_model_service = FeatureModelService()
    statistics_service = StatisticsService()

    # Statistics: total datasets and feature models
    datasets_counter = dataset_service.count_synchronized_datasets()
    feature_models_counter = feature_model_service.count_feature_models()

    # Statistics: total downloads
    total_dataset_downloads = statistics_service.get_datasets_downloaded()
    total_feature_model_downloads = statistics_service.get_feature_models_downloaded()

    # Statistics: total views
    total_dataset_views = statistics_service.get_datasets_viewed()
    total_feature_model_views = statistics_service.get_feature_models_viewed()

    trending_metric, trending_period, trending_datasets = dataset_service.get_trending_datasets(
        request.args.get("trending_metric", "downloads"),
        request.args.get("trending_period", "week"),
    )

    page = render_template(
        "public/index.html",
        datasets=dataset_service.get_top_5_datasets_by_feature_model_count(),
        trending_datasets=trending_datasets,
        trending_metric=trending_metric,
        trending_period=trending_period,
        datasets_counter=datasets_counter,
        feature_models_counter=feature_models_counter,
        total_dataset_downloads=total_dataset_downloads,
        total_feature_model_downloads=total_feature_model_downloads,
        total_dataset_views=total_dataset_views,
        total_feature_model_views=total_feature_model_views,
    )
    response = make_response(page)
    response.cache_control.no_store = True
    return response
