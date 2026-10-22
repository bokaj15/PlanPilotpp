from fasb import interpreter_bindings as ib
from fasb import wrappers_bindings as wb

def exists_subset(MUGS, list_MUGS):
  for m in list_MUGS:
    if m.issubset(MUGS):
      return True
  return False

def exists_proper_subset(MUGS, list_MUGS):
  for m in list_MUGS:
    if  m.issubset(MUGS) and m != MUGS:
      return True
  return False

def dfs(nav, enforce_soft_goal, candidate_goal, activated_goals, list_MUGS):
  S = activated_goals + [enforce_soft_goal]
 
  false_goals = ib.entailment(nav, candidate_goal, S, ['%%'])
  for f_goal in false_goals:
    UGS = set(S + [f_goal])
    if not exists_subset(UGS, list_MUGS):
      list_MUGS.append(UGS)

  false_goal_list = set(false_goals)

  candidate_goal =  [x for x in candidate_goal if x not in false_goal_list]

  for i, g in enumerate(candidate_goal):
    rest = candidate_goal[i+1:]
    if rest:
      dfs(nav, g, rest, activated_goals + [enforce_soft_goal], list_MUGS)

def compute_mugs(lp, clingo_args):
  nav = wb.PyNavigator(lp, clingo_args)
  soft_goal_facets = ib.compute_facets(nav, [],  [r'^softGoal\('])
  all_MUGS = []

  impossible_soft_goals = ib.entailment(nav, ib.atoms(nav), [], ['%%', r'^softGoal\('])

  for g in impossible_soft_goals:
    all_MUGS.append({g})

  for i, soft_goal in enumerate(soft_goal_facets):
    candidate_goals = soft_goal_facets[i+1:]
    if candidate_goals:
      dfs(nav, soft_goal, candidate_goals, [], all_MUGS)

  minimal_MUGS = []
  for m in all_MUGS:
    if not exists_proper_subset(m, all_MUGS):
      minimal_MUGS.append(m)
  return minimal_MUGS


