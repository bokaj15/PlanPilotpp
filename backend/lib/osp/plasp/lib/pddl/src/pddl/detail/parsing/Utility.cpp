#include <pddl/detail/parsing/Utility.h>

#include <pddl/AST.h>
#include <pddl/Exception.h>
#include <pddl/detail/parsing/AtomicFormula.h>
#include <pddl/detail/parsing/Expressions.h>

namespace pddl
{
namespace detail
{

////////////////////////////////////////////////////////////////////////////////////////////////////
//
// Utility
//
////////////////////////////////////////////////////////////////////////////////////////////////////

std::experimental::optional<ast::UtilityFact> parseUtility(Context &context, ASTContext &astContext, VariableStack &variableStack)
{
	auto &tokenizer = context.tokenizer;

	tokenizer.skipWhiteSpace();

	tokenizer.expect<std::string>("(");
	tokenizer.expect<std::string>("=");

	std::experimental::optional<ast::Fact> fact;

	if (!((fact = parseNot<ast::AtomicFormula>(context, astContext, variableStack, parseAtomicFormula))
		|| (fact = parseAtomicFormula(context, astContext, variableStack))))
	{
		throw ParserException(tokenizer.location(), "expected atomic formula in utility declaration");
	}

	const auto weight = tokenizer.get<int32_t>();

	tokenizer.skipWhiteSpace();
	tokenizer.expect<std::string>(")");

	return ast::UtilityFact{std::move(fact.value()), weight};
}

////////////////////////////////////////////////////////////////////////////////////////////////////

}
}
