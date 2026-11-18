#include <pddl/detail/normalization/Problem.h>

#include <pddl/AST.h>
#include <pddl/NormalizedAST.h>
#include <pddl/detail/normalization/InitialState.h>
#include <pddl/detail/normalization/Precondition.h>
#include <pddl/detail/normalization/Fact.h>

namespace pddl
{
namespace detail
{

////////////////////////////////////////////////////////////////////////////////////////////////////
//
// Problem
//
////////////////////////////////////////////////////////////////////////////////////////////////////

normalizedAST::ProblemPointer normalize(ast::ProblemPointer &&problem, normalizedAST::Domain *domain)
{
	auto normalizedProblem = std::make_unique<normalizedAST::Problem>(domain);

	normalizedProblem->name = std::move(problem->name);
	normalizedProblem->objects = std::move(problem->objects);
	normalizedProblem->initialState = normalize(std::move(problem->initialState));

	normalizedProblem->utilities.reserve(problem->utilities.size());

	for (auto &utility : problem->utilities)
		normalizedProblem->utilities.push_back({normalize(std::move(utility.fact)), utility.weight});

	normalizedProblem->bound = problem->bound;

	if (problem->goal)
	{
		NormalizationContext normalizationContext(normalizedProblem->derivedPredicates);
		normalizationContext.derivedPredicateIDStart = domain->derivedPredicates.size() + 1;

		normalizedProblem->goal = normalize(std::move(problem->goal.value()), normalizationContext);
	}

	return normalizedProblem;
}

////////////////////////////////////////////////////////////////////////////////////////////////////

}
}
