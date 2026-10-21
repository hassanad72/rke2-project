# Jenkins CI walkthrough

Flow: Checkout -> Check changes -> Lint -> Test -> Build image -> Scan image -> Push to ECR.

The selected Jenkins node needs Git, Bash, Docker, AWS CLI and its ECR push IAM role.
Ruff, pytest and Trivy run in temporary containers; they do not need host installation.
Python checks install requirements-dev.txt. Only requirements.txt enters the app image.
pytest runs the existing unittest tests and writes JUnit XML for Jenkins test results.

## Failure behavior

- Lint errors, formatting differences, or test failures stop later stages.
- Trivy scans the built local image before publication. Failure to scan stops the build.
- reports/trivy.json contains all reported vulnerability severities, including unfixed findings.
- A second cached scan displays and blocks on High/Critical findings with available fixes.
- Unfixed findings are visible in the full report, but do not fail this initial policy.
- This scans known package vulnerabilities; it is not a guarantee of application security.
- Reports are archived even when a later stage fails. Old report files are removed before checks.

## Pipeline settings

The pipeline has a 20-minute timeout, serial builds, timestamps and retention of the last
10 build records (including their archived artifacts). Retention does not delete ECR images
or local Docker images. The Trivy database cache remains in the workspace for reuse.
The GitHub push trigger still requires a configured GitHub webhook.

## Run checks locally

```sh
python -m pip install -r requirements-dev.txt
ruff check app.py tests
ruff format --check app.py tests
python -m pytest tests -v --junitxml=reports/junit.xml
```

To correct formatting, run `ruff format app.py tests` and commit the changes.
No Kubernetes deployment or image-tag update is performed by CI.

References:
- https://www.jenkins.io/doc/book/pipeline/syntax/
- https://docs.astral.sh/ruff/linter/
- https://trivy.dev/docs/latest/references/configuration/cli/trivy_image/

## Manifest-only changes and loop prevention

Check changes compares the checked-out commit with the previous successful Jenkins commit.
If every changed file is under k8s/, Lint, Test, Build image, Scan image and Push to ECR
are skipped. A webhook can still start a successful run that only checks out and compares Git.
Changes outside k8s/, including application code, tests, requirements, Dockerfile and Jenkinsfile,
run CI normally. Mixed app/manifest commits also run CI. First builds, missing baseline history,
and manual reruns of the same successful commit run full CI.
Comparing against the last successful commit includes changes from failed or batched builds;
it does not inspect only the most recent commit. Git diff errors fail the run instead of skipping it.
A future manifest-update stage must use the same RUN_CI condition. That update stage has
not been added yet. This guard alone does not change deployment image tags or deploy anything.
