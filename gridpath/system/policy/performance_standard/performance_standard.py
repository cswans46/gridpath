# Copyright 2022 (c) Crown Copyright, GC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Performance standard for each performance_standard zone
"""

import csv
import os.path
import pandas as pd

from pyomo.environ import Set, Param, NonNegativeReals, value

from gridpath.auxiliary.db_interface import directories_to_db_values
from gridpath.common_functions import create_results_df, update_results_df
from gridpath.system.policy.performance_standard import PERFORMANCE_STANDARD_Z_PRD_DF

Infinity = float("inf")


def add_model_components(
    m,
    d,
    scenario_directory,
    weather_iteration,
    hydro_iteration,
    availability_iteration,
    subproblem,
    stage,
):
    """

    :param m:
    :param d:
    :return:
    """

    m.PERFORMANCE_STANDARD_ZONE_PERIODS_WITH_PERFORMANCE_STANDARD = Set(
        dimen=2, within=m.PERFORMANCE_STANDARD_ZONES * m.PERIODS
    )
    
    m.PERFORMANCE_STANDARD_ZONE_PERIODS_PROJECTS_WITH_PERFORMANCE_STANDARD = Set(
        dimen=3, within=m.PERFORMANCE_STANDARD_ZONES * m.PERIODS * m.PROJECTS
    )
    
    m.performance_standard_tco2_per_mwh = Param(
        m.PERFORMANCE_STANDARD_ZONE_PERIODS_PROJECTS_WITH_PERFORMANCE_STANDARD,
        within=NonNegativeReals,
        default=Infinity,
    )
    
    m.performance_standard_tco2_per_mw = Param(
        m.PERFORMANCE_STANDARD_ZONE_PERIODS_PROJECTS_WITH_PERFORMANCE_STANDARD,
        within=NonNegativeReals,
        default=Infinity,
    )


def load_model_data(
    m,
    d,
    data_portal,
    scenario_directory,
    weather_iteration,
    hydro_iteration,
    availability_iteration,
    subproblem,
    stage,
):
    """

    :param m:
    :param d:
    :param data_portal:
    :param scenario_directory:
    :param subproblem:
    :param stage:
    :return:
    """
    data_portal.load(
        filename=os.path.join(
            scenario_directory,
            weather_iteration,
            hydro_iteration,
            availability_iteration,
            subproblem,
            stage,
            "inputs",
            "performance_standard.tab",
        ),
        index=m.PERFORMANCE_STANDARD_ZONE_PERIODS_PROJECTS_WITH_PERFORMANCE_STANDARD,
        param=(m.performance_standard_tco2_per_mwh, m.performance_standard_tco2_per_mw),
    )


def get_inputs_from_database(
    scenario_id,
    subscenarios,
    weather_iteration,
    hydro_iteration,
    availability_iteration,
    subproblem,
    stage,
    conn,
):
    """
    :param subscenarios: SubScenarios object with all subscenario info
    :param subproblem:
    :param stage:
    :param conn: database connection
    :return:
    """

    c = conn.cursor()
    performance_standard = c.execute(
        """SELECT performance_standard_zone, period, project, performance_standard_tco2_per_mwh, performance_standard_tco2_per_mw
        FROM inputs_system_performance_standard
        JOIN
        (SELECT period
        FROM inputs_temporal_periods
        WHERE temporal_scenario_id = {}) as relevant_periods
        USING (period)
        JOIN
        (SELECT performance_standard_zone
        FROM inputs_geography_performance_standard_zones
        WHERE performance_standard_zone_scenario_id = {}) as relevant_zones
        using (performance_standard_zone)
        JOIN
        -- Get projects from portfolio only
        (SELECT project
            FROM inputs_project_portfolios
            WHERE project_portfolio_scenario_id = {}
        ) as prj_tbl
        LEFT OUTER JOIN 
        -- Get performance standard zones for those projects
        (SELECT project, performance_standard_zone
            FROM inputs_project_performance_standard_zones
            WHERE project_performance_standard_zone_scenario_id = {}
        ) as prj_ps_zone_tbl
        USING (project)
        -- Filter out projects whose performance standard zone is not one included in 
        -- our performance_standard_zone_scenario_id
        WHERE performance_standard_zone in (
                SELECT performance_standard_zone
                    FROM inputs_geography_performance_standard_zones
                    WHERE performance_standard_zone_scenario_id = {}
        )
        AND subproblem_id = {}
        AND stage_id = {}
        AND project_portfolio_scenario_id = {};
        """.format(
            subscenarios.TEMPORAL_SCENARIO_ID,
            subscenarios.PERFORMANCE_STANDARD_ZONE_SCENARIO_ID,
            subscenarios.PERFORMANCE_STANDARD_SCENARIO_ID,
            subscenarios.PROJECT_PORTFOLIO_SCENARIO_ID,
            subscenarios.PROJECT_PERFORMANCE_STANDARD_ZONE_SCENARIO_ID,
            subscenarios.PERFORMANCE_STANDARD_ZONE_SCENARIO_ID,
            subscenarios.PROJECT_PORTFOLIO_SCENARIO_ID,
            subscenarios.PROJECT_PERFORMANCE_STANDARD_ZONE_SCENARIO_ID,
            subscenarios.PERFORMANCE_STANDARD_ZONE_SCENARIO_ID,
            subproblem,
            stage,
        )
    )

    return performance_standard

def validate_inputs(
    scenario_id,
    subscenarios,
    weather_iteration,
    hydro_iteration,
    availability_iteration,
    subproblem,
    stage,
    conn,
):
    """
    Get inputs from database and validate the inputs
    :param subscenarios: SubScenarios object with all subscenario info
    :param subproblem:
    :param stage:
    :param conn: database connection
    :return:
    """
    pass


def write_model_inputs(
    scenario_directory,
    scenario_id,
    subscenarios,
    weather_iteration,
    hydro_iteration,
    availability_iteration,
    subproblem,
    stage,
    conn,
):
    """
    Get inputs from database and write out the model input
    performance_standard.tab file.
    :param scenario_directory: string, the scenario directory
    :param subscenarios: SubScenarios object with all subscenario info
    :param subproblem:
    :param stage:
    :param conn: database connection
    :return:
    """

    (
        db_weather_iteration,
        db_hydro_iteration,
        db_availability_iteration,
        db_subproblem,
        db_stage,
    ) = directories_to_db_values(
        weather_iteration, hydro_iteration, availability_iteration, subproblem, stage
    )

    performance_standard = get_inputs_from_database(
        scenario_id,
        subscenarios,
        db_weather_iteration,
        db_hydro_iteration,
        db_availability_iteration,
        db_subproblem,
        db_stage,
        conn,
    )

    with open(
        os.path.join(
            scenario_directory,
            weather_iteration,
            hydro_iteration,
            availability_iteration,
            subproblem,
            stage,
            "inputs",
            "performance_standard.tab",
        ),
        "w",
        newline="",
    ) as performance_standard_file:
        writer = csv.writer(
            performance_standard_file, delimiter="\t", lineterminator="\n"
        )

        # Write header
        writer.writerow(
            [
                "performance_standard_zone",
                "period",
                "performance_standard_tco2_per_mwh",
                "performance_standard_tco2_per_mw",
            ]
        )
        for row in performance_standard:
            row = ["." if i is None else i for i in row]
            writer.writerow(row)


def export_results(
    scenario_directory,
    weather_iteration,
    hydro_iteration,
    availability_iteration,
    subproblem,
    stage,
    m,
    d,
):
    """

    :param scenario_directory:
    :param subproblem:
    :param stage:
    :param m:
    :param d:
    :return:
    """
    results_columns = [
        "performance_standard_tco2_per_mwh",
        "performance_standard_tco2_per_mw",
    ]
    data = [
        [
            z,
            p,
            prj,
            float(m.performance_standard_tco2_per_mwh[z, p, prj]),
            float(m.performance_standard_tco2_per_mw[z, p, prj]),
        ]
        for (z, p, prj) in m.PERFORMANCE_STANDARD_ZONE_PERIODS_WITH_PERFORMANCE_STANDARD_PRJS
    ]
    results_df = create_results_df(
        index_columns=["performance_standard_zone", "period", "performance_standard_project"],
        results_columns=results_columns,
        data=data,
    )

    update_results_df(getattr(d, PERFORMANCE_STANDARD_Z_PRD_DF), results_df)
