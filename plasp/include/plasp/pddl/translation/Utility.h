#ifndef __PLASP__PDDL__TRANSLATION__UTILITY_H
#define __PLASP__PDDL__TRANSLATION__UTILITY_H

#include <pddl/NormalizedAST.h>

#include <plasp/TranslatorException.h>

#include <plasp/pddl/translation/Predicate.h>

namespace plasp
{
namespace pddl
{

////////////////////////////////////////////////////////////////////////////////////////////////////
//
// Utility
//
////////////////////////////////////////////////////////////////////////////////////////////////////

inline void translateUtilityFact(colorlog::ColorStream &outputStream, const ::pddl::normalizedAST::UtilityFact &utilityFact)
{
	outputStream << std::endl << colorlog::Function("utility") << "(";

	VariableIDMap variableIDs;

	const auto handlePredicate =
		[&](const ::pddl::normalizedAST::PredicatePointer &predicate, bool isPositive = true)
		{
			translatePredicateToVariable(outputStream, *predicate, variableIDs, isPositive);
		};

	const auto handleNegatedPredicate =
		[&](const ::pddl::normalizedAST::PredicatePointer &predicate)
		{
			return handlePredicate(predicate, false);
		};

	const auto handleDerivedPredicate =
		[&](const ::pddl::normalizedAST::DerivedPredicatePointer &, bool = true)
		{
			throw TranslatorException("derived predicates should not occur in utility declarations");
		};

	const auto handleNegatedDerivedPredicate =
		[&](const ::pddl::normalizedAST::DerivedPredicatePointer &derivedPredicate)
		{
			return handleDerivedPredicate(derivedPredicate, false);
		};

	const auto handleAtomicFormula =
		[&](const ::pddl::normalizedAST::AtomicFormula &atomicFormula)
		{
			atomicFormula.match(handlePredicate, handleDerivedPredicate);
		};

	const auto handleNot =
		[&](const ::pddl::normalizedAST::NotPointer<::pddl::normalizedAST::AtomicFormula> &not_)
		{
			not_->argument.match(handleNegatedPredicate, handleNegatedDerivedPredicate);
		};
  
  utilityFact.fact.match(handleAtomicFormula, handleNot);

	outputStream << ", " << colorlog::Number<int32_t>(utilityFact.weight) << ").";

}

////////////////////////////////////////////////////////////////////////////////////////////////////

}
}

#endif
