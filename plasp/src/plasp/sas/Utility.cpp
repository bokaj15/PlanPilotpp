#include <plasp/sas/Utility.h>

namespace plasp
{
namespace sas
{

////////////////////////////////////////////////////////////////////////////////////////////////////
//
// Utility
//
////////////////////////////////////////////////////////////////////////////////////////////////////

Utility Utility::fromSAS(tokenize::Tokenizer<> &tokenizer, const Variables &variables)
{
	Utility utility;

	tokenizer.expect<std::string>("begin_util");

	const auto numberOfUtilityFacts = tokenizer.get<size_t>();
	utility.m_facts.reserve(numberOfUtilityFacts);

	for (size_t i = 0; i < numberOfUtilityFacts; i++)
  {
    auto fact = AssignedVariable::fromSAS(tokenizer, variables);
    const auto weight = tokenizer.get<int>();

		utility.m_facts.push_back({std::move(fact), weight});
  }

	tokenizer.expect<std::string>("end_util");

	return utility;
}

////////////////////////////////////////////////////////////////////////////////////////////////////

const UtilityFacts &Utility::facts() const
{
	return m_facts;
}

////////////////////////////////////////////////////////////////////////////////////////////////////

}
}
