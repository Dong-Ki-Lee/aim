import os

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from aim.sdk.configs import get_aim_repo_name
from aim.web.configs import AIM_PROFILER_KEY
from aim.web.middlewares.profiler import PyInstrumentProfilerMiddleware
from aim.web.utils import get_root_path


async def http_exception_handler(request, exc):
    message = str(exc.detail)
    detail = None

    if isinstance(exc.detail, dict):
        message = exc.detail.pop('message', message)
        detail = exc.detail.pop('detail', None)

    response = {'message': message}
    if detail:
        response.update({'detail': detail})
    else:
        response.update({'detail': str(exc)})
    return JSONResponse(response, status_code=exc.status_code)


async def fallback_exception_handler(request, exc):
    response = {
        'message': f'\'{type(exc)}\' exception raised!',
        'detail': str(exc)
    }
    return JSONResponse(response, status_code=500)


def create_app():
    app = FastAPI(title=__name__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD'],
        allow_headers=['Origin', 'X-Requested-With',
                       'Content-Type', 'Accept', 'Authorization'],
        allow_credentials=True,
        max_age=86400
    )

    from aim.web.api.runs.views import runs_router
    from aim.web.api.runs.views import add_api_routes
    from aim.web.api.tags.views import tags_router
    from aim.web.api.experiments.views import experiment_router
    from aim.web.api.dashboard_apps.views import dashboard_apps_router
    from aim.web.api.dashboards.views import dashboards_router
    from aim.web.api.projects.views import projects_router
    from aim.web.api.views import statics_router
    from aim.web.configs import AIM_UI_BASE_PATH

    from aim.web.api.projects.project import Project
    from aim.sdk.index_manager import RepoIndexManager

    # The indexing thread has to run in the same process as the uvicorn app itself.
    # This allows sharing state of indexing using memory instead of process synchronization methods.
    index_mng = RepoIndexManager.get_index_manager(Project().repo.path)
    index_mng.start_indexing_thread()

    api_app = FastAPI()
    api_app.add_middleware(GZipMiddleware)
    api_app.add_exception_handler(HTTPException, http_exception_handler)
    api_app.add_exception_handler(Exception, fallback_exception_handler)

    if os.environ.get(AIM_PROFILER_KEY) == "1":
        api_app.add_middleware(PyInstrumentProfilerMiddleware,
                               repo_path=os.path.join(get_root_path(), get_aim_repo_name()))

    add_api_routes()

    api_app.include_router(dashboard_apps_router, prefix='/apps')
    api_app.include_router(dashboards_router, prefix='/dashboards')
    api_app.include_router(experiment_router, prefix='/experiments')
    api_app.include_router(projects_router, prefix='/projects')
    api_app.include_router(runs_router, prefix='/runs')
    api_app.include_router(tags_router, prefix='/tags')

    base_path = os.environ.get(AIM_UI_BASE_PATH, '')

    app.mount(f'{base_path}/api', api_app)
    static_files_app = FastAPI()

    static_files_app.include_router(statics_router)
    app.mount(f'{base_path}/', static_files_app)

    return app
