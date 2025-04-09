﻿using Google.OrTools.Sat;
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public class Solver
{
    [System.Serializable]
    public struct Job
    {
        public Task[] tasks;
    }

    [System.Serializable]
    public struct Task
    {
        static public Dictionary<TaskType, int> taskPriority = new Dictionary<TaskType, int> {
            { TaskType.Charger, 5 },
            { TaskType.Input, 4 },
            { TaskType.Shelf, 3 },
            { TaskType.Packer, 2 },
            { TaskType.Devivery, 1 }
        };

        public enum TaskType
        {
            Charger,
            Input,
            Shelf,
            Packer,
            Devivery
        }

        public int startLocationId;
        public int endLocationId;
        public int serviceTime;
        public TaskType type;
    }

    public static int[][] Solve(int numRobots, Job[] jobs, int[][] travelTimes, long horizon = int.MaxValue, bool verbose = true)
    {
        CpModel model = new CpModel();

        Task[] allTasks = jobs.Select(ele => ele.tasks).Aggregate(new List<Task>(), (acc, ele) => { acc.AddRange(ele); return acc; }).ToArray();
        long totalTaskCount = allTasks.LongLength;
        int k = 0;

        IntVar[] startVars = new IntVar[totalTaskCount];
        IntVar[] endVars = new IntVar[totalTaskCount];
        IntervalVar[] taskIntervals = new IntervalVar[totalTaskCount];

        foreach (Task[] tasks in jobs.Select(ele => ele.tasks))
        {
            for (int i = k; i < tasks.Length + k; i++)
            {
                startVars[i] = model.NewIntVar(0, horizon, $"start_{i}");
                endVars[i] = model.NewIntVar(0, horizon, $"end_{i}");
                taskIntervals[i] = model.NewIntervalVar(startVars[i], travelTimes[allTasks[i].startLocationId][allTasks[i].endLocationId] + allTasks[i].serviceTime, endVars[i], $"interval_{i}");
            }

            for (int i = k; i < tasks.Length + k; i++)
            {
                for (int j = k; j < tasks.Length + k; j++)
                {
                    if (Task.taskPriority[allTasks[i].type] > Task.taskPriority[allTasks[j].type])
                    {
                        if (verbose)
                            Debug.Log($"model.Add(startVars[{j}] >= endVars[{i}])");
                        model.Add(startVars[j] >= endVars[i]);
                    }
                }
            }

            k += tasks.Length;
        }

        IntervalVar[][] robotTaskIntervals = new IntervalVar[totalTaskCount][];
        IntVar[][] isAssigned = new IntVar[totalTaskCount][];

        for (int i = 0; i < totalTaskCount; i++)
        {
            robotTaskIntervals[i] = new IntervalVar[numRobots];
            isAssigned[i] = new IntVar[numRobots];
            for (int r = 0; r < numRobots; r++)
            {
                isAssigned[i][r] = model.NewBoolVar($"is_assigned_task_{i}_robot_{r}");
                robotTaskIntervals[i][r] = model.NewOptionalIntervalVar(startVars[i], travelTimes[allTasks[i].startLocationId][allTasks[i].endLocationId] + allTasks[i].serviceTime, endVars[i], isAssigned[i][r], $"interval_task_{i}_robot_{r}");
            }
        }

        for (int r = 0; r < numRobots; r++)
        {
            List<IntervalVar> intervalsForRobot = new List<IntervalVar>();
            for (int i = 0; i < totalTaskCount; i++)
            {
                intervalsForRobot.Add(robotTaskIntervals[i][r]);
            }
            if (verbose)
                Debug.Log("model.AddNoOverlap(intervalsForRobot)");
            model.AddNoOverlap(intervalsForRobot);
        }

        for (int i = 0; i < totalTaskCount; i++)
        {
            if (verbose)
                Debug.Log($"model.Add(LinearExpr.Sum(isAssigned[{i}]) == 1)");
            model.Add(LinearExpr.Sum(isAssigned[i]) == 1);
        }

        IntVar makespan = model.NewIntVar(0, horizon, "makespan");
        model.AddMaxEquality(makespan, endVars);
        model.Minimize(makespan);

        for (int r = 0; r < numRobots; r++)
        {
            for (int i = 0; i < totalTaskCount; i++)
            {
                for (int j = 0; j < totalTaskCount; j++)
                {
                    if (i == j) continue;

                    ILiteral[] bothAssigned = new ILiteral[] { isAssigned[i][r], isAssigned[j][r] };

                    IntVar iBeforeJ = model.NewBoolVar($"task_{i}_before_task_{j}_robot_{r}");
                    IntVar jBeforeI = model.NewBoolVar($"task_{j}_before_task_{i}_robot_{r}");

                    if (verbose)
                        Debug.Log($"model.Add(iBeforeJ + jBeforeI == 1).OnlyEnforceIf(bothAssigned)");
                    model.Add(iBeforeJ + jBeforeI == 1).OnlyEnforceIf(bothAssigned);
                    if (verbose)
                        Debug.Log($"model.Add(iBeforeJ + jBeforeI == 0).OnlyEnforceIf(isAssigned[{i}][{r}].Not())");
                    model.Add(iBeforeJ + jBeforeI == 0).OnlyEnforceIf(isAssigned[i][r].Not());
                    if (verbose)
                        Debug.Log($"model.Add(iBeforeJ + jBeforeI == 0).OnlyEnforceIf(isAssigned[{j}][{r}].Not())");
                    model.Add(iBeforeJ + jBeforeI == 0).OnlyEnforceIf(isAssigned[j][r].Not());

                    if (verbose)
                        Debug.Log($"model.Add(startVars[{j}] >= endVars[{i}] + {travelTimes[allTasks[i].endLocationId][allTasks[j].startLocationId]}).OnlyEnforceIf(iBeforeJ)");
                    model.Add(startVars[j] >= endVars[i] + travelTimes[allTasks[i].endLocationId][allTasks[j].startLocationId]).OnlyEnforceIf(iBeforeJ);
                    if (verbose)
                        Debug.Log($"model.Add(startVars[{i}] >= endVars[{j}] + {travelTimes[allTasks[j].endLocationId][allTasks[i].startLocationId]}).OnlyEnforceIf(jBeforeI)");
                    model.Add(startVars[i] >= endVars[j] + travelTimes[allTasks[j].endLocationId][allTasks[i].startLocationId]).OnlyEnforceIf(jBeforeI);
                }
            }
        }

        CpSolver solver = new CpSolver();

        CpSolverStatus status = solver.Solve(model);

        if (status == CpSolverStatus.Optimal || status == CpSolverStatus.Feasible)
        {
            if (verbose)
                Debug.Log("Found a solution with status: " + status.ToString());

            int[][] results = new int[numRobots][];
            for (int r = 0; r < numRobots; r++)
            {
                var tempResult = new List<KeyValuePair<int, long>>();
                for (int i = 0; i < totalTaskCount; i++)
                {
                    if (solver.BooleanValue(isAssigned[i][r]))
                    {
                        tempResult.Add(new KeyValuePair<int, long>(i, solver.Value(startVars[i])));
                    }
                }
                tempResult.Sort((ele1, ele2) => ele1.Value.CompareTo(ele2.Value));
                results[r] = tempResult.Select(ele => ele.Key).ToArray();
            }

            return results;
        }
        else
        {
            if (verbose)
                Debug.Log("No solution found.");
            return null;
        }
    }
}
